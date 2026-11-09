import json
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import chess.engine
import pygame

import eloify_features as ef
import main as eloify


REAL_UCI_SCRIPT = r"""
import json
import sys
import time
import chess

mode = sys.argv[1]
log_path = sys.argv[2]
board = chess.Board()

def log(ev):
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ev) + "\n")

for raw in sys.stdin:
    line = raw.strip()
    if line == "uci":
        print(f"id name Engine-{mode}", flush=True)
        print("option name Threads type spin default 8 min 1 max 64", flush=True)
        print("option name Hash type spin default 128 min 1 max 4096", flush=True)
        print("option name Use Sleeping Threads type check default false", flush=True)
        print("uciok", flush=True)
    elif line.startswith("setoption "):
        log({"cmd": "setoption", "raw": line})
    elif line == "isready":
        print("readyok", flush=True)
    elif line == "ucinewgame":
        board = chess.Board()
    elif line.startswith("position "):
        parts = line.split()
        idx = 1
        if parts[idx] == "startpos":
            board = chess.Board()
            idx += 1
        elif parts[idx] == "fen":
            board = chess.Board(" ".join(parts[idx + 1:idx + 7]))
            idx += 7
        if idx < len(parts) and parts[idx] == "moves":
            for u in parts[idx + 1:]:
                board.push_uci(u)
    elif line.startswith("go"):
        log({"cmd": "go", "raw": line})
        if mode == "slow_timeout":
            time.sleep(0.35)
            mv = next(iter(board.legal_moves))
            print(f"info depth 6 nps 125000 score cp 15", flush=True)
            print(f"bestmove {mv.uci()}", flush=True)
            continue
        if mode == "eval":
            vals = {1: 100, 2: 320, 3: 330, 4: 500, 5: 900, 6: 0}
            wm = sum(vals[p.piece_type] for p in board.piece_map().values() if p.color)
            bm = sum(vals[p.piece_type] for p in board.piece_map().values() if not p.color)
            pov = (wm - bm + 25) if board.turn else (bm - wm + 25)
            print(f"info depth 18 nps 980000 score cp {pov}", flush=True)
            mv = next(iter(board.legal_moves))
            print(f"bestmove {mv.uci()}", flush=True)
            continue
        chosen = None
        for m in board.legal_moves:
            board.push(m)
            mate = board.is_checkmate()
            board.pop()
            if mate:
                chosen = m
                break
        if chosen is None:
            if mode == "strong":
                for pref in ("e2e4", "e7e5", "f1c4", "b8c6", "d1h5", "d8h4", "h5f7"):
                    mv = chess.Move.from_uci(pref)
                    if mv in board.legal_moves:
                        chosen = mv
                        break
            elif mode == "weak":
                for pref in ("f2f3", "f7f6", "g2g4", "g7g5"):
                    mv = chess.Move.from_uci(pref)
                    if mv in board.legal_moves:
                        chosen = mv
                        break
        if chosen is None:
            chosen = next(iter(board.legal_moves))
        print("info depth 10 nps 450000 score cp 42", flush=True)
        print(f"bestmove {chosen.uci()}", flush=True)
    elif line == "stop":
        if list(board.legal_moves):
            print(f"bestmove {next(iter(board.legal_moves)).uci()}", flush=True)
        else:
            print("bestmove 0000", flush=True)
    elif line == "quit":
        break
"""


def _make_headless_app():
    with patch.object(pygame.display, "set_mode",
                      side_effect=lambda size: pygame.Surface(size)):
        app = eloify.EloifyApp()
    return app


class ChessRulesAndClocksTests(unittest.TestCase):
    def test_no_300_move_adjudication_game_keeps_playing_past_300_plies(self):
        """Games must not stop at 300 plies; they continue until a real rule ends them."""
        worker = eloify.TournamentWorker("target.exe", queue.Queue())
        ply_count = [0]

        # Construct a sequence that resets halfmove_clock via pawn pushes periodically
        # and avoids 3-fold repetition by advancing pawns every ~30 moves!
        def fake_play(board, role):
            ply_count[0] += 1
            if ply_count[0] <= 320:
                # Every 40 plies push a pawn if available so 50-move rule doesn't trigger
                if board.halfmove_clock >= 70:
                    for mv in board.legal_moves:
                        p = board.piece_at(mv.from_square)
                        if p and p.piece_type == chess.PAWN:
                            return SimpleNamespace(move=mv)
                # Pick a legal move that does not cause threefold repetition or stalemate
                for mv in board.legal_moves:
                    board.push(mv)
                    bad = board.is_game_over(claim_draw=True)
                    board.pop()
                    if not bad:
                        return SimpleNamespace(move=mv)
            # After 320 plies, trigger 50-move draw cleanly on the next quiet piece move
            board.halfmove_clock = 99
            for mv in board.legal_moves:
                p = board.piece_at(mv.from_square)
                if p and p.piece_type != chess.PAWN and not board.is_capture(mv):
                    return SimpleNamespace(move=mv)
            return SimpleNamespace(move=next(iter(board.legal_moves)))

        worker._safe_play = fake_play
        res = worker.play_game(target_is_white=True)
        self.assertGreater(worker.current_move_number, 305)
        self.assertEqual(res, "D")
        self.assertNotIn("adjudicated", worker.last_game_result.lower())

    def test_fifty_move_rule_triggers_draw(self):
        # K+R vs K+R shuffling without captures for 100 half-moves (50 full moves)
        worker = eloify.TournamentWorker("target.exe", queue.Queue())
        orig_reset = worker.board.reset
        worker.board.reset = lambda: (
            orig_reset(),
            worker.board.set_fen("4k2r/8/8/8/8/8/8/R3K3 w - - 0 1"),
        )

        # Visit distinct rook/king squares without repeating any position 3 times
        def non_repeating_shuffle(board, role):
            for mv in board.legal_moves:
                if board.is_capture(mv):
                    continue
                board.push(mv)
                rep3 = board.is_repetition(3)
                stalemate = board.is_stalemate()
                insuff = board.is_insufficient_material()
                board.pop()
                if not rep3 and not stalemate and not insuff:
                    return SimpleNamespace(move=mv)
            return SimpleNamespace(move=next(iter(board.legal_moves)))

        worker._safe_play = non_repeating_shuffle
        res = worker.play_game(target_is_white=True)
        self.assertEqual(res, "D")
        self.assertEqual(worker.current_move_number, 100)
        self.assertIn("FIFTY_MOVES", worker.last_game_result)

    def test_threefold_repetition_triggers_draw_immediately_not_fivefold(self):
        # 1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 -> 8 plies = 3rd occurrence of startpos!
        moves = [
            "g1f3", "g8f6", "f3g1", "f6g8",
            "g1f3", "g8f6", "f3g1", "f6g8",
            # Extra moves that would only be reached if fivefold were used:
            "g1f3", "g8f6", "f3g1", "f6g8",
        ]
        it = iter(moves)
        worker = eloify.TournamentWorker("target.exe", queue.Queue())
        worker._safe_play = lambda b, r: SimpleNamespace(move=chess.Move.from_uci(next(it)))
        res = worker.play_game(target_is_white=True)
        self.assertEqual(res, "D")
        self.assertEqual(worker.current_move_number, 8)
        self.assertIn("THREEFOLD_REPETITION", worker.last_game_result)

    def test_30_second_chess_timer_initializes_records_and_forfeits_on_timeout(self):
        worker_default = eloify.TournamentWorker("target.exe", queue.Queue())
        self.assertEqual(worker_default.chess_clock_initial, 30.0)
        self.assertEqual(worker_default.white_clock, 30.0)
        self.assertEqual(worker_default.black_clock, 30.0)

        # Target (White) stalls past a short test clock -> loses on time
        worker_flag = eloify.TournamentWorker(
            "target.exe", queue.Queue(), settings={"chess_clock": 0.05}
        )

        def slow_target(board, role):
            if role == "target":
                time.sleep(0.09)
            return SimpleNamespace(move=next(iter(board.legal_moves)))

        worker_flag._safe_play = slow_target
        res = worker_flag.play_game(target_is_white=True)
        self.assertEqual(res, "L")
        self.assertIn("on time", worker_flag.last_game_result)
        self.assertEqual(worker_flag.white_clock, 0.0)

        # Opponent (Black) stalls -> Target wins on time
        worker_opp_flag = eloify.TournamentWorker(
            "target.exe", queue.Queue(), settings={"chess_clock": 0.06}
        )

        def slow_opponent(board, role):
            if role == "opponent":
                time.sleep(0.09)
            return SimpleNamespace(move=next(iter(board.legal_moves)))

        worker_opp_flag._safe_play = slow_opponent
        res2 = worker_opp_flag.play_game(target_is_white=True)
        self.assertEqual(res2, "W")
        self.assertIn("on time", worker_opp_flag.last_game_result)
        self.assertEqual(worker_opp_flag.black_clock, 0.0)
        self.assertEqual(len(worker_opp_flag.game_records), 1)
        self.assertEqual(len(worker_opp_flag.game_records[0]["plies"]), 1)
        ply0 = worker_opp_flag.game_records[0]["plies"][0]
        self.assertIn("move_time", ply0)
        self.assertIn("white_left", ply0)
        self.assertIn("black_left", ply0)


class AudioMuteAndVolumeTests(unittest.TestCase):
    def test_mute_button_volume_slider_and_m_key_during_running(self):
        app = _make_headless_app()
        try:
            app.state = "RUNNING"
            app.worker = eloify.TournamentWorker("target.exe", queue.Queue())
            app.start_time = time.time()

            # Drag volume slider to ~40%
            vr = app.running_vol_rect
            target_x = vr.x + int(vr.w * 0.40)
            app.handle_click((target_x, vr.centery))
            app.handle_mouse_motion((vr.x + int(vr.w * 0.25), vr.centery))
            app.handle_mouse_up((vr.x + int(vr.w * 0.25), vr.centery))
            self.assertAlmostEqual(app.audio_volume, 0.25, delta=0.03)
            self.assertFalse(app.audio_muted)
            if app.drumroll_sound is not None:
                self.assertAlmostEqual(app.drumroll_sound.get_volume(), app.audio_volume, delta=0.05)

            # Click Mute button
            app.handle_click(app.running_mute_rect.center)
            self.assertTrue(app.audio_muted)
            if app.drumroll_sound is not None:
                self.assertAlmostEqual(app.drumroll_sound.get_volume(), 0.0, delta=0.01)

            # Press M shortcut to unmute
            app.handle_key_down(SimpleNamespace(key=pygame.K_m, mod=0))
            self.assertFalse(app.audio_muted)
            app.draw_running()
        finally:
            app._stop_aux_workers()


class EtaScaleSkipAndConfirmationTests(unittest.TestCase):
    def test_eta_estimation_and_elo_scale_bar_300_to_4010(self):
        eta0 = ef.estimate_tournament_eta_seconds(
            elapsed_s=0.0, games_played=0, total_games=40, time_per_move=0.1
        )
        self.assertGreater(eta0, 10.0)
        eta_half = ef.estimate_tournament_eta_seconds(
            elapsed_s=60.0, games_played=20, total_games=40, time_per_move=0.1
        )
        self.assertAlmostEqual(eta_half, 60.0, delta=5.0)
        self.assertTrue(ef.format_eta(eta_half).startswith("~"))
        self.assertEqual(ef.format_eta(0), "00:00")

        # Scale 300 -> 0.0, 4010 -> 1.0
        self.assertAlmostEqual(ef.elo_scale_fraction(300), 0.0)
        self.assertAlmostEqual(ef.elo_scale_fraction(4010), 1.0)
        mid = ef.elo_scale_fraction(2155)
        self.assertTrue(0.49 < mid < 0.51)

        pygame.init()
        surf = pygame.Surface((240, 32))
        pal = ef.get_theme_palette("dark", "emerald")
        ef.draw_elo_scale_bar(surf, pygame.Rect(10, 6, 200, 16), 2850, pal)

    def test_upcoming_opponent_skip_and_side_progress_scroll_and_back_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, "uci_eng.py")
            script.write_text(REAL_UCI_SCRIPT, encoding="utf-8")
            logs = {k: str(Path(tmp, f"{k}.jsonl")) for k in ("t", "o0", "o1", "o2", "adj")}
            specs = {
                "t":  ("strong", logs["t"]),
                "o0": ("weak", logs["o0"]),
                "o1": ("weak", logs["o1"]),
                "o2": ("weak", logs["o2"]),
                "adj": ("eval", logs["adj"]),
            }
            real_popen = chess.engine.SimpleEngine.popen

            def fake_popen(proto, path):
                mode, lg = specs[path]
                return real_popen(proto, [sys.executable, str(script), mode, lg], timeout=3)

            with patch.object(eloify, "OPPONENTS", [("o0", 800), ("o1", 1500), ("o2", 2200)]), \
                 patch.object(eloify, "ADJUDICATOR_PATH", ""), \
                 patch.object(eloify, "GAMES_PER_OPPONENT", 2), \
                 patch.object(chess.engine.SimpleEngine, "popen", side_effect=fake_popen):
                q = queue.Queue()
                worker = eloify.TournamentWorker("t", q, settings={"time": 0.02})
                self.assertEqual(worker.total_games, 6)
                # Skip opponent index 1 ("o1", 1500) before worker reaches it!
                skipped = worker.toggle_skip_opponent(1)
                self.assertTrue(skipped)
                self.assertEqual(worker.total_games, 4)
                worker.run()

                # Verify o1 was never launched, while o0 and o2 completed
                self.assertFalse(Path(logs["o1"]).exists())
                self.assertEqual(worker.games_played, 4)
                snap = worker.get_schedule_snapshot()
                self.assertEqual([e["status"] for e in snap], ["done", "skipped", "done"])

        # Test UI side scroll & Back to Menu confirmation modal
        app = _make_headless_app()
        try:
            app.state = "RUNNING"
            app.worker = eloify.TournamentWorker("target.exe", queue.Queue())
            app.start_time = time.time()
            app.draw_running()
            # Click a Skip hitbox in the live side menu
            self.assertGreater(len(app._running_skip_hitboxes), 0)
            opp_idx, btn_rect = app._running_skip_hitboxes[0]
            app.handle_click(btn_rect.center)
            self.assertTrue(app.worker.is_opponent_skipped(opp_idx))

            # Scroll side menu
            app.handle_mouse_wheel(SimpleNamespace(y=-3))
            self.assertFalse(app.running_opp_autoscroll)

            # Click Back to Menu -> opens confirmation, does NOT reset yet!
            app.handle_click(app.running_back_rect.center)
            self.assertTrue(app.confirm_back_to_menu)
            self.assertEqual(app.state, "RUNNING")

            # Click Cancel -> stays in RUNNING
            _, cancel_r, confirm_r = app._get_confirm_modal_rects()
            app.handle_click(cancel_r.center)
            self.assertFalse(app.confirm_back_to_menu)
            self.assertEqual(app.state, "RUNNING")

            # Open confirmation again and confirm -> returns to MENU
            app.handle_click(app.running_back_rect.center)
            app.handle_click(confirm_r.center)
            self.assertFalse(app.confirm_back_to_menu)
            self.assertEqual(app.state, "MENU")
        finally:
            app._stop_aux_workers()


class VisualCustomizationAndThemesTests(unittest.TestCase):
    def test_auto_rotate_hide_coords_board_skins_custom_rgb_piece_styles_and_themes(self):
        app = _make_headless_app()
        try:
            # 1) Hide coordinates changes rendered board pixels
            bg_coords = eloify._get_board_bg(320, show_coords=True, flipped=False)
            bg_no_coords = eloify._get_board_bg(320, show_coords=False, flipped=False)
            self.assertNotEqual(
                pygame.image.tostring(bg_coords, "RGB"),
                pygame.image.tostring(bg_no_coords, "RGB"),
            )

            # 2) Auto-rotate flips e1 from bottom row to top row
            _, y_normal = eloify._sq_to_center_px(chess.E1, (0, 0), sq_size=50, flipped=False)
            _, y_flipped = eloify._sq_to_center_px(chess.E1, (0, 0), sq_size=50, flipped=True)
            self.assertGreater(y_normal, 300)
            self.assertLess(y_flipped, 100)

            # 3) Custom RGB board skin via Settings Tab 1
            app.open_settings(tab=1)
            sliders = app._get_rgb_slider_rects()
            tr0 = sliders[0][0]
            app.handle_click((tr0.x + int(tr0.w * 0.8), tr0.centery))
            app.handle_mouse_up((tr0.x + int(tr0.w * 0.8), tr0.centery))
            self.assertEqual(app.board_skin, "custom")
            app.draw_settings_overlay()

            # 4) All piece styles render distinct non-empty surfaces
            for style_key in ef.PIECE_STYLE_ORDER:
                surf = eloify._get_piece_surface("N", 48, style=style_key)
                self.assertGreater(surf.get_width(), 10)
                surf_b = eloify._get_piece_surface("q", 48, style=style_key)
                self.assertGreater(surf_b.get_width(), 10)

            # 5) Light mode & Dark mode + all 6 accents render cleanly
            for mode in ("dark", "light"):
                for accent in ef.ACCENT_ORDER:
                    app._apply_theme(mode, accent)
                    app.state = "MENU"
                    app.draw_menu()
                    app.open_settings(tab=2)
                    app.draw_settings_overlay()
                    app.settings_save()
            app._apply_theme("light", "ocean")
            self.assertGreater(sum(eloify.BACKGROUND), 600)
            app._apply_theme("dark", "emerald")
            self.assertLess(sum(eloify.BACKGROUND), 150)
        finally:
            app._stop_aux_workers()


class PlaylistReplayEvalAndTelemetryTests(unittest.TestCase):
    def test_playlist_live_eval_replay_navigation_move_quality_and_data_tracking(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, "uci_eng.py")
            script.write_text(REAL_UCI_SCRIPT, encoding="utf-8")
            logs = {
                k: str(Path(tmp, f"{k}.jsonl"))
                for k in ("eng_a", "eng_b", "opp", "live_adj", "replay_adj")
            }

            # 1) Verify LiveEvalWorker uses low Threads=1 & Hash=16, while
            #    ReplayEvalWorker uses stronger multi-thread & larger Hash!
            live_worker = ef.LiveEvalWorker(
                [sys.executable, str(script), "eval", logs["live_adj"]],
                protocol_cls=eloify.CompatibleUciProtocol,
            )
            live_worker.start()
            after_e4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
            live_worker.request_fen(after_e4)
            deadline = time.time() + 3.0
            while after_e4 not in live_worker.cache and time.time() < deadline:
                time.sleep(0.03)
            live_worker.stop()
            live_worker.join(timeout=2.0)
            self.assertIn(after_e4, live_worker.cache)
            live_ev = [
                json.loads(line)["raw"]
                for line in Path(logs["live_adj"]).read_text(encoding="utf-8").splitlines()
                if '"setoption"' in line
            ]
            self.assertTrue(any("name Threads value 1" in s for s in live_ev))
            self.assertTrue(any("name Hash value 16" in s for s in live_ev))

            replay_worker = ef.ReplayEvalWorker(
                [sys.executable, str(script), "eval", logs["replay_adj"]],
                threads=4,
                hash_mb=256,
                protocol_cls=eloify.CompatibleUciProtocol,
            )
            replay_worker.start()
            replay_worker.request_fen(after_e4)
            deadline = time.time() + 3.0
            while after_e4 not in replay_worker.cache and time.time() < deadline:
                time.sleep(0.03)
            replay_worker.stop()
            replay_worker.join(timeout=2.0)
            self.assertIn(after_e4, replay_worker.cache)
            self.assertEqual(replay_worker.cache[after_e4][2], 18)
            replay_ev = [
                json.loads(line)["raw"]
                for line in Path(logs["replay_adj"]).read_text(encoding="utf-8").splitlines()
                if '"setoption"' in line
            ]
            self.assertTrue(any("name Threads value 4" in s for s in replay_ev))
            self.assertTrue(any("name Hash value 256" in s for s in replay_ev))

            # 2) Run a 2-engine Playlist with Engine Data Tracking & Move-Quality Elo enabled,
            #    then verify scrollable DONE screen + Game Move Replay navigation (A/D & Left/Right)!
            specs = {
                "eng_a": ("strong", logs["eng_a"]),
                "eng_b": ("weak", logs["eng_b"]),
                "opp":   ("weak", logs["opp"]),
                "adj":   ("eval", logs["live_adj"]),
            }
            real_popen = chess.engine.SimpleEngine.popen

            def fake_popen(proto, path):
                if isinstance(path, (list, tuple)):
                    return real_popen(proto, path, timeout=3)
                mode, lg = specs[path]
                return real_popen(proto, [sys.executable, str(script), mode, lg], timeout=3)

            app = _make_headless_app()
            try:
                with patch.object(eloify, "OPPONENTS", [("opp", 1200)]), \
                     patch.object(eloify, "ADJUDICATOR_PATH", "adj"), \
                     patch.object(eloify, "GAMES_PER_OPPONENT", 2), \
                     patch.object(chess.engine.SimpleEngine, "popen", side_effect=fake_popen):
                    # Queue 2 engines via playlist, test reorder, then run both!
                    app.browse_mode = "playlist_add"
                    app._accept_browsed_engine("eng_b")
                    app.browse_mode = "playlist_add"
                    app._accept_browsed_engine("eng_a")
                    self.assertEqual(app.engine_playlist, ["eng_b", "eng_a"])
                    app.draw_menu()
                    # Click ↑ on row #2 to move eng_a first in line!
                    up_rects = [r for act, idx, r in app._playlist_row_hitboxes if act == "up" and idx == 1]
                    self.assertEqual(len(up_rects), 1)
                    app.handle_click(up_rects[0].center)
                    self.assertEqual(app.engine_playlist, ["eng_a", "eng_b"])

                    app.cfg_engine_data_tracking = True
                    app.cfg_move_quality_elo = True
                    app.cfg_time = 0.02
                    app.cfg_auto_rotate_board = True
                    app.start_tournament()

                    deadline = time.time() + 15.0
                    while app.state != "DONE" and time.time() < deadline:
                        app.process_queue()
                        if app.state == "RUNNING":
                            app.draw_running()
                        time.sleep(0.02)

                    self.assertEqual(app.state, "DONE")
                    self.assertEqual(len(app.playlist_results), 2)
                    res_a, res_b = app.playlist_results
                    self.assertGreater(res_a["estimated_elo"], res_b["estimated_elo"])

                    # Verify Engine Data Tracking captured real OS RAM & UCI NPS
                    self.assertIsNotNone(res_a["resource_summary"])
                    self.assertGreater(res_a["resource_summary"]["peak_ram_mb"], 0.1)
                    self.assertGreater(res_a["resource_summary"]["live_nps"], 0)

                    # Verify per-game Move-Quality Elo was computed
                    self.assertIsNotNone(res_a["move_quality"])
                    self.assertTrue(300.0 <= res_a["move_quality"]["move_quality_elo"] <= 4050.0)

                    # Verify Calculating ELO progress bar screen renders
                    app._draw_mystery_reveal(0.8)

                    # Fast-forward past reveal and render scrollable DONE screen
                    app.done_start_time = time.time() - 5.0
                    app.draw_done()
                    self.assertEqual(len(app._done_playlist_hitboxes), 2)
                    self.assertGreaterEqual(len(app._done_game_hitboxes), 2)

                    # Switch selected engine in Playlist Leaderboard on DONE
                    app.handle_click(app._done_playlist_hitboxes[1][1].center)
                    self.assertEqual(app.selected_result_idx, 1)
                    app.handle_click(app._done_playlist_hitboxes[0][1].center)
                    self.assertEqual(app.selected_result_idx, 0)
                    app.draw_done()

                    # Open Game #1 in Interactive Replay Viewer
                    game_rec, game_rect = app._done_game_hitboxes[0]
                    app.handle_click(game_rect.center)
                    self.assertIsNotNone(app.replay_game)
                    self.assertEqual(app.replay_ply, 0)
                    app.draw_done()

                    # Navigate forward with Right arrow and 'D', backward with Left and 'A'
                    app.handle_key_down(SimpleNamespace(key=pygame.K_RIGHT, mod=0))
                    self.assertEqual(app.replay_ply, 1)
                    app.handle_key_down(SimpleNamespace(key=pygame.K_d, mod=0))
                    self.assertEqual(app.replay_ply, 2)
                    app.draw_done()
                    # Verify per-move time & remaining clocks exist on navigated ply
                    cur_ply = app.replay_game["plies"][app.replay_ply - 1]
                    self.assertGreaterEqual(cur_ply["move_time"], 0.0)
                    self.assertLessEqual(cur_ply["white_left"], 30.0)
                    self.assertLessEqual(cur_ply["black_left"], 30.0)

                    app.handle_key_down(SimpleNamespace(key=pygame.K_a, mod=0))
                    self.assertEqual(app.replay_ply, 1)
                    app.handle_key_down(SimpleNamespace(key=pygame.K_LEFT, mod=0))
                    self.assertEqual(app.replay_ply, 0)

                    # Exit Replay back to DONE results
                    app.handle_key_down(SimpleNamespace(key=pygame.K_ESCAPE, mod=0))
                    self.assertIsNone(app.replay_game)
            finally:
                app._stop_aux_workers()
    
    def test_move_quality_elo_rates_strong_moves_higher_than_blunders(self):
        strong_plies = [
            {
                "ply": 1, "uci": "e2e4", "san": "e4", "mover_is_white": True,
                "fen_before": chess.STARTING_FEN,
                "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "eval_before_cp": 25, "eval_after_cp": 22,
            },
            {
                "ply": 3, "uci": "g1f3", "san": "Nf3", "mover_is_white": True,
                "fen_before": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
                "fen_after": "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
                "eval_before_cp": 30, "eval_after_cp": 28,
            },
        ]
        blunder_plies = [
            {
                "ply": 1, "uci": "f2f3", "san": "f3", "mover_is_white": True,
                "fen_before": chess.STARTING_FEN,
                "fen_after": "rnbqkbnr/pppppppp/8/8/8/5P2/PPPPP1PP/RNBQKBNR b KQkq - 0 1",
                "eval_before_cp": 25, "eval_after_cp": -160,
            },
            {
                "ply": 3, "uci": "g2g4", "san": "g4", "mover_is_white": True,
                "fen_before": "rnbqkbnr/pppp1ppp/8/4p3/8/5P2/PPPPP1PP/RNBQKBNR w KQkq - 0 2",
                "fen_after": "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2",
                "eval_before_cp": -150, "eval_after_cp": -900,
            },
        ]
        strong_mq = ef.compute_game_move_quality_elo(strong_plies, target_is_white=True)
        blunder_mq = ef.compute_game_move_quality_elo(blunder_plies, target_is_white=True)
        self.assertGreater(strong_mq["move_quality_elo"], 3400)
        self.assertGreater(strong_mq["accuracy_pct"], 95.0)
        self.assertLess(blunder_mq["move_quality_elo"], 1500)
        self.assertLess(blunder_mq["accuracy_pct"], 40.0)


if __name__ == "__main__":
    unittest.main()
