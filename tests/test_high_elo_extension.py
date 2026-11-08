"""Tests for automatic >3600 Elo time-odds extension, paired openings, and UI."""
import ast
from collections import deque
from datetime import datetime
import math
import os
from pathlib import Path
import queue
import random
import re
import sys
import tempfile
import threading
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import chess
import chess.engine
import pygame


ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))

ns = dict(
    chess=chess,
    pygame=pygame,
    deque=deque,
    datetime=datetime,
    math=math,
    os=os,
    queue=queue,
    random=random,
    re=re,
    sys=SimpleNamespace(platform="linux"),
    tempfile=tempfile,
    threading=threading,
    time=time,
    traceback=traceback,
)

wanted_assigns = {
    "_UNSET",
    "ADJUDICATOR_PATH",
    "GAMES_PER_OPPONENT",
    "TIME_LIMIT",
    "MAX_MOVE_RETRIES",
    "HIGH_ELO_TIME_ODDS_TIERS",
    "HIGH_ELO_TRIGGER_RATING",
    "HIGH_ELO_TOP_BRACKET",
    "HIGH_ELO_MIN_TOP_SCORE",
    "HIGH_ELO_DEFAULT_ANCHOR_RATING",
    "HIGH_ELO_OPENINGS",
    "RESULTS_VISIBLE_ROWS",
    "ENGINE_QUIT_TIMEOUT",
    "LEGACY_MOVETIME_GRACE",
    "WINDOW_WIDTH",
    "WINDOW_HEIGHT",
    "FPS",
    "BACKGROUND",
    "PANEL",
    "PANEL_HOVER",
    "BORDER",
    "TEXT_COLOR",
    "DIM_TEXT",
    "ACCENT",
    "GOLD",
    "ERROR_COLOR",
    "WIN_COLOR",
    "LOSS_COLOR",
    "DRAW_COLOR",
    "BOARD_SIZE",
    "SQUARE_SIZE",
    "BOARD_POS",
    "INFO_POS",
    "BOARD_LIGHT",
    "BOARD_DARK",
    "MOVE_ANIM_DURATION",
    "REVEAL_DURATION",
    "ELO_POP_DURATION",
    "_FONT_CACHE",
    "_FONT_FAMILY",
    "_TEXT_CACHE",
    "_PIECE_FONT_CACHE",
    "PIECE_GLYPHS",
    "_PIECE_SURFACE_CACHE",
    "_BOARD_BG_CACHE",
    "_LAST_MOVE_HL",
    "_BOARD_FEN_CACHE",
}

wanted_defs = {
    "OpponentDead",
    "TournamentAborted",
    "_exception_message",
    "_engine_failure_details",
    "_save_error_log",
    "estimate_elo_vs_pool",
    "confidence_interval_95",
    "format_time_multiplier",
    "_normalize_opponent_results",
    "should_run_high_elo_extension",
    "select_high_elo_anchor",
    "build_high_elo_tiers",
    "get_pool_max_extended_elo",
    "select_extension_openings",
    "_detect_total_ram_mb",
    "get_recommended_hash_mb",
    "get_recommended_threads",
    "is_maia_engine",
    "CompatibleUciProtocol",
    "build_engine_config",
    "apply_engine_config",
    "get_engine_name",
    "format_config",
    "ease_out_back",
    "_init_font_family",
    "_get_font",
    "_render_text",
    "draw_text",
    "draw_text_centered",
    "draw_section",
    "draw_rounded_panel",
    "_glyph_renders",
    "_get_piece_font",
    "_get_piece_surface",
    "_sq_to_center_px",
    "_draw_piece_at",
    "_get_board_bg",
    "_get_last_move_highlight",
    "_get_board",
    "MoveAnimation",
    "draw_board",
    "TournamentWorker",
}

nodes = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted_defs:
        nodes.append(node)
    elif isinstance(node, ast.Assign):
        targets = set()
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.add(target.id)
            elif isinstance(target, ast.Tuple):
                targets.update(elt.id for elt in target.elts if isinstance(elt, ast.Name))
        if targets & wanted_assigns:
            nodes.append(node)

app_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EloifyApp")
ui_methods = {
    "_make_menu_bg_gradient",
    "_init_menu_particles",
    "_update_menu_particles",
    "_draw_menu_particles",
    "_get_menu_title_glow",
    "_draw_menu_button",
    "_draw_edit_button",
    "_draw_stat_panel",
    "process_queue",
    "handle_key_down",
    "handle_mouse_wheel",
    "_update_animation",
    "_spawn_confetti",
    "_update_and_draw_confetti",
    "_draw_mystery_reveal",
    "_draw_elo_pop",
    "draw_menu",
    "draw_running",
    "draw_done",
    "shutdown",
}
nodes.append(
    ast.ClassDef(
        name="HarnessApp",
        bases=[],
        keywords=[],
        decorator_list=[],
        body=[n for n in app_node.body if isinstance(n, ast.FunctionDef) and n.name in ui_methods],
    )
)

ns["OPPONENTS"] = [("sf17.exe", 3595), ("sf18.exe", 3620), ("sf19.exe", 3660)]
ns["ERROR_LOG_DIR"] = os.path.join(tempfile.gettempdir(), "eloify-test-logs")
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "main.py", "exec"), ns)


FAKE_UCI_ENGINE = """
import json
import sys
import time
import chess

name, behavior, logfile = sys.argv[1:]
crash_once_marker = logfile + ".crashed"
board = chess.Board()

def log_event(obj):
    with open(logfile, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj) + "\\n")

for raw in sys.stdin:
    line = raw.strip()
    if line == "uci":
        print(f"id name {name}", flush=True)
        print("option name Threads type spin default 1 min 1 max 64", flush=True)
        print("option name Hash type spin default 16 min 1 max 4096", flush=True)
        print("uciok", flush=True)
    elif line == "ucinewgame":
        log_event({"cmd": "ucinewgame"})
    elif line == "isready":
        print("readyok", flush=True)
    elif line.startswith("position "):
        tokens = line.split()
        idx = 1
        if tokens[idx] == "startpos":
            board = chess.Board()
            idx += 1
        elif tokens[idx] == "fen":
            fen_parts = tokens[idx + 1:idx + 7]
            board = chess.Board(" ".join(fen_parts))
            idx += 7
        moves = []
        if idx < len(tokens) and tokens[idx] == "moves":
            moves = tokens[idx + 1:]
            for uci in moves:
                board.push_uci(uci)
        log_event({"cmd": "position", "raw": line, "moves": moves, "fen": board.fen()})
    elif line.startswith("go"):
        tokens = line.split()
        movetime = int(tokens[tokens.index("movetime") + 1]) if "movetime" in tokens else None
        log_event({"cmd": "go", "movetime": movetime, "ply": len(board.move_stack)})
        if behavior == "crash_once" and not __import__("os").path.exists(crash_once_marker):
            open(crash_once_marker, "w").close()
            sys.exit(2)
        if behavior == "hang_long" and (movetime or 0) >= 200:
            time.sleep(30)
            break
        if behavior == "analyse":
            piece_vals = {1: 100, 2: 300, 3: 300, 4: 500, 5: 900, 6: 0}
            white_mat = sum(piece_vals[p.piece_type] for p in board.piece_map().values() if p.color)
            black_mat = sum(piece_vals[p.piece_type] for p in board.piece_map().values() if not p.color)
            pov = (white_mat - black_mat) if board.turn else (black_mat - white_mat)
            print(f"info depth 10 score cp {pov}", flush=True)
            print("bestmove " + next(iter(board.legal_moves)).uci(), flush=True)
            continue
        # Deterministic fast games:
        # "strong" finds mate-in-1 if available and picks first legal move;
        # "fool_victim" cooperates into Fool's Mate from startpos so tests run in milliseconds!
        chosen = None
        for m in board.legal_moves:
            board.push(m)
            is_mate = board.is_checkmate()
            board.pop()
            if is_mate:
                chosen = m
                break
        if chosen is None:
            piece_vals = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
            def mat_score(mv):
                cap = board.piece_at(mv.to_square)
                gain = piece_vals.get(cap.piece_type, 0) if cap else 0
                board.push(mv)
                chk = 0.5 if board.is_check() else 0.0
                # Check if destination square is attacked
                attacked = board.is_attacked_by(board.turn, mv.to_square)
                mover = board.piece_at(mv.to_square)
                hang = piece_vals.get(mover.piece_type, 0) if (attacked and mover) else 0
                board.pop()
                return gain + chk - 0.8 * hang

            if behavior == "weak":
                for pref in ("f2f3", "g2g4", "f7f6", "g7g5"):
                    mv = chess.Move.from_uci(pref)
                    if mv in board.legal_moves:
                        chosen = mv
                        break
                if chosen is None:
                    chosen = min(board.legal_moves, key=mat_score)
            elif behavior == "strong":
                for pref in ("e2e4", "e7e5", "d1h5", "d8h4"):
                    mv = chess.Move.from_uci(pref)
                    if mv in board.legal_moves and len(board.move_stack) < 4:
                        chosen = mv
                        break
                if chosen is None:
                    chosen = max(board.legal_moves, key=mat_score)
        if chosen is None:
            chosen = next(iter(board.legal_moves))
        print(f"bestmove {chosen.uci()}", flush=True)
    elif line == "quit":
        break
"""


class TierAndAnchorTests(unittest.TestCase):
    def test_stockfish_19_anchor_builds_calibrated_fixed_tiers_above_4000(self):
        tiers = ns["build_high_elo_tiers"]("sf19.exe", 3660)
        self.assertEqual(
            tiers,
            [
                ("sf19.exe", 3740, 2.0),
                ("sf19.exe", 3815, 4.0),
                ("sf19.exe", 3885, 8.0),
                ("sf19.exe", 3950, 16.0),
                ("sf19.exe", 4010, 32.0),
            ],
        )

    def test_pool_max_extended_elo_summary(self):
        count, max_elo = ns["get_pool_max_extended_elo"](
            opponents=[("random.exe", 300), ("sf18.exe", 3620), ("sf19.exe", 3660)],
            adjudicator_path="sf19.exe",
        )
        self.assertEqual((count, max_elo), (5, 4010))

    def test_fallback_to_sf17_1_when_sf18_and_sf19_missing(self):
        anchor = ns["select_high_elo_anchor"](
            [("sf16.exe", 3560), ("sf17_1.exe", 3595)],
            adjudicator_path="sf19.exe",
            adjudicator_available=True,
        )
        self.assertEqual(anchor, ("sf17_1.exe", 3595))
        tiers = ns["build_high_elo_tiers"](*anchor)
        self.assertEqual([r for _, r, _ in tiers], [3675, 3750, 3820, 3885, 3945])
        self.assertTrue(all(r > 3600 for _, r, _ in tiers))

    def test_adjudicator_rescues_anchor_when_high_opponents_unavailable(self):
        anchor = ns["select_high_elo_anchor"](
            [("fox.exe", 3060)],
            adjudicator_path="C:/Engines/Stockfish 19/sf19.exe",
            adjudicator_available=True,
            configured_opponents=[("C:/Engines/Stockfish 19/sf19.exe", 3660)],
        )
        self.assertEqual(anchor, ("C:/Engines/Stockfish 19/sf19.exe", 3660))

    def test_maia_is_never_selected_as_adjudicator_anchor(self):
        anchor = ns["select_high_elo_anchor"](
            [],
            adjudicator_path="C:/Engines/Maia/maia-1900.bat",
            adjudicator_available=True,
        )
        self.assertIsNone(anchor)
        count, max_elo = ns["get_pool_max_extended_elo"](
            opponents=[("C:/Engines/Maia/maia-1900.bat", 1900)],
            adjudicator_path=None,
        )
        self.assertEqual((count, max_elo), (0, 1900))

    def test_weak_only_anchor_filters_out_sub_3600_tiers(self):
        self.assertEqual(ns["build_high_elo_tiers"]("fox.exe", 3060), [])
        self.assertEqual(
            ns["build_high_elo_tiers"]("sf8.exe", 3320),
            [("sf8.exe", 3610, 16.0), ("sf8.exe", 3670, 32.0)],
        )


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.low_ratings = [300, 1500, 2400, 2800, 3100, 3320, 3480]
        self.top_ratings = [3505, 3535, 3560, 3585, 3595, 3620, 3660]

    def test_top_engine_qualifies(self):
        results = [("low", r, 2, 0, 0) for r in self.low_ratings]
        results += [("top", r, 1, 1, 0) for r in self.top_ratings]
        self.assertTrue(ns["should_run_high_elo_extension"](results))

    def test_startpos_draw_wall_at_50_percent_still_qualifies(self):
        # A 3600+ engine that sweeps <3500 and draws every startpos game vs 3505-3660
        # must still trigger the extension so paired book openings break the draw wall.
        results = [("low", r, 2, 0, 0) for r in self.low_ratings]
        results += [("top", r, 0, 2, 0) for r in self.top_ratings]
        self.assertTrue(ns["should_run_high_elo_extension"](results))

    def test_perfect_sweep_qualifies(self):
        results = [(r, 2, 0, 0) for r in self.low_ratings + self.top_ratings]
        self.assertTrue(ns["should_run_high_elo_extension"](results))

    def test_mid_and_sub_3500_engines_do_not_qualify(self):
        results = [("low", r, 2, 0, 0) for r in self.low_ratings]
        results += [("top", r, 0, 1, 1) if r < 3570 else ("top", r, 0, 0, 2)
                    for r in self.top_ratings]
        self.assertFalse(ns["should_run_high_elo_extension"](results))

    def test_farming_many_weak_engines_without_top_bracket_score_rejected(self):
        results = [("weak", 2500, 2, 0, 0) for _ in range(45)]
        results += [("top", r, 0, 0, 2) for r in self.top_ratings]
        results[-1] = ("top", 3660, 0, 1, 1)
        self.assertFalse(ns["should_run_high_elo_extension"](results))

    def test_empty_or_all_loss_rejected(self):
        self.assertFalse(ns["should_run_high_elo_extension"]([]))
        self.assertFalse(ns["should_run_high_elo_extension"]([("sf19", 3660, 0, 0, 2)]))


class OpeningBookTests(unittest.TestCase):
    def test_all_curated_openings_are_legal_distinct_and_non_terminal(self):
        seen_fens = set()
        self.assertGreaterEqual(len(ns["HIGH_ELO_OPENINGS"]), 10)
        for name, moves in ns["HIGH_ELO_OPENINGS"]:
            with self.subTest(opening=name):
                board = chess.Board()
                self.assertGreaterEqual(len(moves), 8)
                for uci in moves:
                    move = chess.Move.from_uci(uci)
                    self.assertIn(move, board.legal_moves)
                    board.push(move)
                self.assertFalse(board.is_game_over())
                self.assertFalse(board.is_check())
                seen_fens.add(board.board_fen())
        self.assertEqual(len(seen_fens), len(ns["HIGH_ELO_OPENINGS"]))

    def test_paired_schedule_uses_same_opening_for_both_colors_and_varies_tiers(self):
        rng = random.Random(12345)
        schedule = ns["select_extension_openings"](5, games_per_opponent=2, rng=rng)
        self.assertEqual(len(schedule), 5)
        tier_openings = []
        for games in schedule:
            self.assertEqual(len(games), 2)
            self.assertIsNotNone(games[0])
            self.assertEqual(games[0], games[1])
            tier_openings.append(games[0][0])
        self.assertEqual(len(set(tier_openings)), 5)

    def test_four_game_and_odd_game_schedules(self):
        sched4 = ns["select_extension_openings"](3, games_per_opponent=4, rng=random.Random(7))
        for games in sched4:
            self.assertEqual(len(games), 4)
            self.assertEqual(games[0], games[1])
            self.assertEqual(games[2], games[3])
            self.assertNotEqual(games[0], games[2])

        sched3 = ns["select_extension_openings"](2, games_per_opponent=3, rng=random.Random(7))
        for games in sched3:
            self.assertEqual(len(games), 3)
            self.assertEqual(games[0], games[1])
            self.assertIsNone(games[2])


class HighEloEstimationTests(unittest.TestCase):
    def test_estimates_smoothly_beyond_3600_and_4000(self):
        tiers = [3505, 3560, 3620, 3660, 3740, 3815, 3885, 3950, 4010]
        # Score matching a ~3900 Elo engine
        pool = []
        for r in tiers:
            p = 1.0 / (1.0 + 10.0 ** ((r - 3900.0) / 400.0))
            # Use fractional game counts equivalent via 100-game scaling to check solver accuracy
            w = round(p * 100)
            l = 100 - w
            pool.append((r, w, 0, l))
        kind, elo = ns["estimate_elo_vs_pool"](pool)
        self.assertEqual(kind, "ok")
        self.assertAlmostEqual(elo, 3900.0, delta=6.0)

    def test_no_artificial_5000_elo_ceiling_and_sweep_lower_bound(self):
        sweep = [(3660, 2, 0, 0), (4010, 2, 0, 0)]
        self.assertEqual(ns["estimate_elo_vs_pool"](sweep), ("lower_bound", 4410))

        extreme = [(5200, 3, 1, 0), (5400, 1, 1, 2)]
        kind, elo = ns["estimate_elo_vs_pool"](extreme)
        self.assertEqual(kind, "ok")
        self.assertGreater(elo, 5200)


class ExtensionTournamentSubprocessTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.script = Path(self.folder.name, "uci_fixture.py")
        self.script.write_text(FAKE_UCI_ENGINE, encoding="utf-8")
        self.logs = {}

    def _make_engine_spec(self, tag, name, behavior):
        log_path = Path(self.folder.name, f"{tag}.jsonl")
        self.logs[tag] = log_path
        return tag, (name, behavior, str(log_path))

    def _read_events(self, tag):
        import json
        log_path = self.logs[tag]
        if not log_path.exists():
            return []
        return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line]

    def test_top_engine_runs_fixed_time_odds_and_paired_openings_while_main_pool_uses_startpos(self):
        target_key, target_spec = self._make_engine_spec("target", "SuperEngine 1.0", "strong")
        adj_key, adj_spec = self._make_engine_spec("adj", "Adjudicator SF19", "analyse")
        opp1_key, opp1_spec = self._make_engine_spec("opp_sf17", "Stockfish 17.1", "weak")
        opp2_key, opp2_spec = self._make_engine_spec("opp_sf19", "Stockfish 19", "weak")
        specs = {
            target_key: target_spec,
            adj_key: adj_spec,
            opp1_key: opp1_spec,
            opp2_key: opp2_spec,
        }

        real_popen = chess.engine.SimpleEngine.popen

        def fake_popen(protocol, path):
            name, behavior, log_file = specs[path]
            return real_popen(
                protocol,
                [sys.executable, str(self.script), name, behavior, log_file],
                timeout=3,
            )

        test_tiers = ((2, 80), (4, 155), (8, 225))
        with patch.dict(
            ns,
            OPPONENTS=[(opp1_key, 3595), (opp2_key, 3660)],
            ADJUDICATOR_PATH=adj_key,
            HIGH_ELO_TIME_ODDS_TIERS=test_tiers,
            GAMES_PER_OPPONENT=2,
        ), patch.object(chess.engine.SimpleEngine, "popen", side_effect=fake_popen):
            q = queue.Queue()
            worker = ns["TournamentWorker"](
                target_key,
                q,
                settings={"time": 0.03, "threads": 1, "hash": 16},
                rng=random.Random(99),
            )
            worker.run()

        self.assertTrue(worker.high_elo_extended)
        self.assertEqual(worker.extension_start_index, 2)
        self.assertEqual(worker.games_played, 10)  # 4 standard + 6 extended
        self.assertEqual(worker.total_games, 10)
        self.assertEqual(
            [(name, rating) for name, rating, _, _, _ in worker.per_opponent_results],
            [
                ("Stockfish 17.1", 3595),
                ("Stockfish 19", 3660),
                ("Stockfish 19 (2x time)", 3740),
                ("Stockfish 19 (4x time)", 3815),
                ("Stockfish 19 (8x time)", 3885),
            ],
        )

        # Standard opponent (SF 17.1) must start from startpos (ply 0 or 1) and 30 ms movetime.
        opp1_events = self._read_events(opp1_key)
        opp1_goes = [e for e in opp1_events if e["cmd"] == "go"]
        self.assertTrue(all(e["movetime"] == 30 for e in opp1_goes))
        first_opp1_plies = [e["ply"] for e in opp1_goes if e["ply"] in (0, 1)]
        self.assertEqual(len(first_opp1_plies), 2)

        # Target always searches at 1x time (30 ms), even during 2x/4x/8x extension tiers.
        target_goes = [e for e in self._read_events(target_key) if e["cmd"] == "go"]
        self.assertTrue(all(e["movetime"] == 30 for e in target_goes))

        # Anchor SF 19 searched at 30 ms in standard pool, then 60 ms, 120 ms, 240 ms in extension!
        sf19_events = self._read_events(opp2_key)
        sf19_movetimes = {e["movetime"] for e in sf19_events if e["cmd"] == "go"}
        self.assertEqual(sf19_movetimes, {30, 60, 120, 240})

        # Verify every game received ucinewgame, standard games used startpos,
        # and extended games started from paired book openings (>= 10 plies).
        def games_from_events(events):
            games = []
            current = None
            for ev in events:
                if ev["cmd"] == "ucinewgame":
                    if current is not None:
                        games.append(current)
                    current = {"positions": [], "goes": []}
                elif current is not None:
                    if ev["cmd"] == "position":
                        current["positions"].append(ev)
                    elif ev["cmd"] == "go":
                        current["goes"].append(ev)
            if current is not None:
                games.append(current)
            return games

        sf19_games = games_from_events(sf19_events)
        self.assertEqual(len(sf19_games), 8)  # 2 standard + 6 extended
        self.assertTrue(all(g["goes"][0]["ply"] in (0, 1) for g in sf19_games[:2]))
        ext_sf19_games = sf19_games[2:]
        self.assertEqual([g["goes"][0]["movetime"] for g in ext_sf19_games],
                         [60, 60, 120, 120, 240, 240])
        self.assertTrue(all(g["goes"][0]["ply"] >= 10 for g in ext_sf19_games))

        # Verify target received ucinewgame on all 10 games and each 2-game extended
        # pair shared the exact same opening move sequence for White and Black!
        target_games = games_from_events(self._read_events(target_key))
        self.assertEqual(len(target_games), 10)
        self.assertTrue(all(len(g["positions"][0]["moves"]) <= 1 for g in target_games[:4]))
        ext_openings_seen = []
        for g_idx, g in enumerate(target_games[4:]):
            first_moves = g["positions"][0]["moves"]
            # On odd game_idx (Target plays Black), opponent already played 1 move after book.
            book_len = len(first_moves) - (1 if g_idx % 2 == 1 else 0)
            self.assertGreaterEqual(book_len, 10)
            ext_openings_seen.append(tuple(first_moves[:book_len]))
        self.assertEqual(ext_openings_seen[0], ext_openings_seen[1])
        self.assertEqual(ext_openings_seen[2], ext_openings_seen[3])
        self.assertEqual(ext_openings_seen[4], ext_openings_seen[5])
        self.assertEqual(len({ext_openings_seen[0], ext_openings_seen[2], ext_openings_seen[4]}), 3)

        done_msgs = [payload for kind, payload in list(q.queue) if kind == "done"]
        self.assertEqual(len(done_msgs), 1)
        (est_kind, est_elo), _ = done_msgs[0]
        self.assertIn(est_kind, ("ok", "lower_bound"))
        self.assertGreater(est_elo, 3800)

    def test_weaker_engine_does_not_trigger_extension(self):
        target_key, target_spec = self._make_engine_spec("weak_target", "WeakBot", "weak")
        adj_key, adj_spec = self._make_engine_spec("adj", "Adjudicator SF19", "analyse")
        opp_key, opp_spec = self._make_engine_spec("opp_sf19", "Stockfish 19", "strong")
        specs = {target_key: target_spec, adj_key: adj_spec, opp_key: opp_spec}

        real_popen = chess.engine.SimpleEngine.popen

        def fake_popen(protocol, path):
            name, behavior, log_file = specs[path]
            return real_popen(
                protocol,
                [sys.executable, str(self.script), name, behavior, log_file],
                timeout=3,
            )

        with patch.dict(
            ns,
            OPPONENTS=[(opp_key, 3660)],
            ADJUDICATOR_PATH=adj_key,
            GAMES_PER_OPPONENT=2,
        ), patch.object(chess.engine.SimpleEngine, "popen", side_effect=fake_popen):
            q = queue.Queue()
            worker = ns["TournamentWorker"](target_key, q, settings={"time": 0.03})
            worker.run()

        self.assertFalse(worker.high_elo_extended)
        self.assertEqual(worker.games_played, 2)
        sf19_movetimes = {e["movetime"] for e in self._read_events(opp_key) if e["cmd"] == "go"}
        self.assertEqual(sf19_movetimes, {30})

    def test_opponent_reload_during_extension_preserves_time_odds_and_label(self):
        target_key, target_spec = self._make_engine_spec("target", "SuperEngine", "strong")
        opp_key, opp_spec = self._make_engine_spec("opp_crash", "Stockfish 19", "crash_once")
        specs = {target_key: target_spec, opp_key: opp_spec}

        real_popen = chess.engine.SimpleEngine.popen

        def fake_popen(protocol, path):
            name, behavior, log_file = specs[path]
            return real_popen(
                protocol,
                [sys.executable, str(self.script), name, behavior, log_file],
                timeout=3,
            )

        with patch.object(chess.engine.LOGGER, "warning"), patch.object(
            chess.engine.SimpleEngine, "popen", side_effect=fake_popen
        ):
            worker = ns["TournamentWorker"](
                target_key,
                queue.Queue(),
                settings={"time": 0.04, "threads": 2, "hash": 32},
            )
            worker.target_engine = worker._launch_engine(target_key)
            try:
                played, _ = worker._play_opponent_match(
                    opp_key,
                    3815,
                    0,
                    "Extended tier 2",
                    time_multiplier=4.0,
                    openings_for_games=[ns["HIGH_ELO_OPENINGS"][0], ns["HIGH_ELO_OPENINGS"][0]],
                )
                self.assertTrue(played)
                self.assertEqual(worker.per_opponent_results[0][0], "Stockfish 19 (4x time)")
                self.assertEqual(worker.per_opponent_results[0][1], 3815)
                opp_goes = [e for e in self._read_events(opp_key) if e["cmd"] == "go"]
                self.assertGreaterEqual(len(opp_goes), 2)
                self.assertTrue(all(e["movetime"] == 160 for e in opp_goes))
            finally:
                worker._kill_engine(worker.target_engine)

    def test_stop_interrupts_long_time_odds_search_cleanly(self):
        target_key, target_spec = self._make_engine_spec("target", "SuperEngine", "strong")
        adj_key, adj_spec = self._make_engine_spec("adj", "Adjudicator SF19", "analyse")
        opp_key, opp_spec = self._make_engine_spec("opp_hang", "Stockfish 19", "hang_long")
        specs = {target_key: target_spec, adj_key: adj_spec, opp_key: opp_spec}

        real_popen = chess.engine.SimpleEngine.popen

        def fake_popen(protocol, path):
            name, behavior, log_file = specs[path]
            return real_popen(
                protocol,
                [sys.executable, str(self.script), name, behavior, log_file],
                timeout=3,
            )

        with patch.object(chess.engine.LOGGER, "warning"), patch.dict(
            ns,
            OPPONENTS=[(opp_key, 3660)],
            ADJUDICATOR_PATH=adj_key,
            HIGH_ELO_TIME_ODDS_TIERS=((8, 225),),
            GAMES_PER_OPPONENT=2,
        ), patch.object(chess.engine.SimpleEngine, "popen", side_effect=fake_popen):
            q = queue.Queue()
            worker = ns["TournamentWorker"](target_key, q, settings={"time": 0.03})
            worker.start()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if any(e.get("movetime") == 240 for e in self._read_events(opp_key) if e["cmd"] == "go"):
                    break
                time.sleep(0.02)
            stop_start = time.monotonic()
            worker.stop()
            worker.join(timeout=2.0)
            self.assertFalse(worker.is_alive())
            self.assertLess(time.monotonic() - stop_start, 1.5)
            errors = [payload for kind, payload in list(q.queue) if kind == "error"]
            self.assertEqual(errors, [])


class ResultsPresentationTests(unittest.TestCase):
    def test_done_autoscrolls_for_extended_run_and_supports_wheel_and_keys(self):
        app = ns["HarnessApp"]()
        app.progress_queue = queue.Queue()
        app.state = "RUNNING"
        app.error_text = None
        app.drumroll_sound = None
        rows = [(f"Engine {i}", 2400 + i * 20, 2, 0, 0) for i in range(20)]
        rows += [(f"Stockfish 19 ({m}x time)", 3660 + b, 1, 1, 0)
                 for m, b in ns["HIGH_ELO_TIME_ODDS_TIERS"]]
        app.worker = SimpleNamespace(
            high_elo_extended=True,
            extension_start_index=20,
            per_opponent_results=rows,
        )
        app.progress_queue.put(("done", (("ok", 3860.0), 95.0)))
        app.process_queue()

        expected_max = len(rows) - ns["RESULTS_VISIBLE_ROWS"]
        self.assertEqual(app.state, "DONE")
        self.assertEqual(app.results_scroll, expected_max)

        app.handle_mouse_wheel(SimpleNamespace(y=2))
        self.assertEqual(app.results_scroll, expected_max - 6)
        app.handle_key_down(SimpleNamespace(key=pygame.K_HOME, mod=0))
        self.assertEqual(app.results_scroll, 0)
        app.handle_key_down(SimpleNamespace(key=pygame.K_END, mod=0))
        self.assertEqual(app.results_scroll, expected_max)

    def test_headless_menu_running_and_done_rendering(self):
        with patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}):
            pygame.init()
            try:
                ns["_init_font_family"]()
                app = ns["HarnessApp"]()
                app.screen = pygame.display.set_mode((ns["WINDOW_WIDTH"], ns["WINDOW_HEIGHT"]))
                app.mouse_pos = (0, 0)
                app._menu_time = 0.0
                app._menu_title_glow = None
                app._menu_bg_gradient = app._make_menu_bg_gradient()
                app._init_menu_particles()
                app.cfg_cpu_cores = 8
                app.cfg_threads = 4
                app.cfg_hash = 512
                app.cfg_time = 0.1
                app.edit_system_rect = pygame.Rect(400, 186, 60, 26)
                app.browse_rect = pygame.Rect(60, 505, 420, 70)
                app.start_rect = pygame.Rect(520, 505, 420, 70)
                app.status_text = "Ready"
                app.target_path = "/tmp/super_engine"
                app.draw_menu()

                app.start_time = time.time() - 42
                app.animation = None
                app.last_animated_fen = chess.STARTING_FEN
                app.last_animated_counter = 0
                app.last_move_from = None
                app.last_move_to = None
                app.worker = SimpleNamespace(
                    high_elo_extended=True,
                    extension_start_index=2,
                    current_opponent_index=5,
                    target_name="SuperEngine",
                    opponent_name="Stockfish 19 (16x time)",
                    opponent_rating=3950,
                    target_config_str="T=4, H=512MB",
                    opponent_config_str="T=4, H=512MB, Move=1.60s (16x)",
                    games_played=8,
                    total_games=10,
                    wins=6,
                    draws=2,
                    losses=0,
                    current_fen_shared=chess.STARTING_FEN,
                    target_is_white=True,
                    current_opening_name="Sicilian Najdorf",
                    current_move_number=14,
                    last_move_san="Bg5",
                    last_move_uci="c1g5",
                    total_move_counter=1,
                    recent_moves=["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6"],
                    last_game_result="Target wins (1-0)",
                    per_opponent_results=[
                        (f"Opponent {i}", 2500 + i * 50, 2, 0, 0) for i in range(20)
                    ] + [
                        ("Stockfish 19 (16x time)", 3950, 1, 1, 0),
                        ("Stockfish 19 (32x time)", 4010, 0, 2, 0),
                    ],
                )
                app.draw_running()

                app.error_text = None
                app.estimated_elo = 3925.0
                app.estimate_kind = "ok"
                app.confidence = 92.0
                app.done_start_time = time.time() - 10.0
                app.confetti = []
                app.confetti_spawned = False
                app.celebration_sound = None
                app._elo_surface_cache = None
                app.results_scroll = 9
                app.draw_done()
            finally:
                pygame.quit()


if __name__ == "__main__":
    unittest.main()
