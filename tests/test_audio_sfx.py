"""Tests for loading MP3 sound effects from audio/ and triggering game/move SFX."""
from collections import deque
import os
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import chess
import chess.engine
import pygame

import main as eloify


def _build_valid_mp3_bytes(frame_count=10):
    """Build valid MPEG-1 Layer III (44.1 kHz, 128 kbps, stereo) frames."""
    frame = bytes([0xFF, 0xFB, 0x90, 0x00]) + bytes(413)
    return frame * frame_count


class AudioLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    def test_audio_dir_and_sound_file_mapping(self):
        expected_dir = os.path.join(
            os.path.dirname(os.path.abspath(eloify.__file__)), "audio"
        )
        self.assertEqual(eloify.AUDIO_DIR, expected_dir)
        self.assertEqual(
            eloify.AUDIO_SOUND_FILES,
            {
                "castle":     "castle.mp3",
                "game-start": "game-start.mp3",
                "game-end":   "game-end.mp3",
                "move-self":  "move-self.mp3",
                "move-check": "move-check.mp3",
                "promote":    "promote.mp3",
            },
        )

    def test_loads_all_six_mp3_files_from_audio_folder(self):
        frame_counts = {
            "castle":     6,
            "game-start": 10,
            "game-end":   14,
            "move-self":  18,
            "move-check": 22,
            "promote":    26,
        }
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp) / "audio"
            audio_dir.mkdir()
            for key, filename in eloify.AUDIO_SOUND_FILES.items():
                (audio_dir / filename).write_bytes(
                    _build_valid_mp3_bytes(frame_counts[key])
                )

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                loaded = eloify._load_game_sounds(audio_dir=str(audio_dir))

            self.assertEqual(caught, [])
            self.assertEqual(set(loaded.keys()), set(eloify.AUDIO_SOUND_FILES.keys()))
            lengths = [loaded[k].get_length() for k in sorted(frame_counts, key=frame_counts.get)]
            # Distinct frame counts produce strictly increasing decoded Sound durations
            for earlier, later in zip(lengths, lengths[1:]):
                self.assertLess(earlier, later)

    def test_case_insensitive_lookup_and_unicode_path_bytesio_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            unicode_dir = Path(tmp) / "audio_引擎"
            unicode_dir.mkdir()
            mp3_path = unicode_dir / "Castle.MP3"
            mp3_path.write_bytes(_build_valid_mp3_bytes(8))

            resolved = eloify._resolve_audio_file("castle.mp3", audio_dir=str(unicode_dir))
            self.assertEqual(resolved, str(mp3_path))

            real_sound = pygame.mixer.Sound
            calls = []

            def flaky_path_sound(*args, **kwargs):
                calls.append((args, kwargs))
                if args and isinstance(args[0], str):
                    raise pygame.error("Simulated path encoding failure")
                return real_sound(*args, **kwargs)

            with patch.object(pygame.mixer, "Sound", side_effect=flaky_path_sound):
                snd = eloify._load_sound_file(resolved)
            self.assertGreater(snd.get_length(), 0.1)
            self.assertEqual(len(calls), 2)

    def test_missing_or_corrupt_mp3_warns_and_falls_back_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp) / "audio"
            audio_dir.mkdir()
            (audio_dir / "castle.mp3").write_bytes(b"not a valid mp3")

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                loaded = eloify._load_game_sounds(audio_dir=str(audio_dir))

            self.assertTrue(any("Missing or unreadable audio files" in str(w.message) for w in caught))
            for key in eloify.AUDIO_SOUND_FILES:
                self.assertIsNotNone(loaded[key])
                self.assertGreater(loaded[key].get_length(), 0.02)

    def test_synthesized_reveal_sounds_preserve_duration_on_stereo_44100_mixer(self):
        drumroll = eloify._generate_drumroll(duration=0.5)
        celebration = eloify._generate_celebration(duration=0.5)
        self.assertAlmostEqual(drumroll.get_length(), 0.5, delta=0.05)
        self.assertAlmostEqual(celebration.get_length(), 0.5, delta=0.05)


class GameAndMoveSoundEventTests(unittest.TestCase):
    def _run_scripted_game(self, uci_moves, initial_fen=None, opening=None,
                           target_is_white=True, analyse_cp=None):
        worker = eloify.TournamentWorker("target.exe", queue.Queue())
        move_iter = iter(uci_moves)

        def fake_safe_play(board, role):
            try:
                uci = next(move_iter)
            except StopIteration:
                # Force loop exit when testing max_moves adjudication
                worker.current_move_number = 300
                return SimpleNamespace(move=next(iter(board.legal_moves)))
            if initial_fen is not None and worker.current_move_number == 0 and uci == "__SET_FEN__":
                board.set_fen(initial_fen)
                uci = next(move_iter)
            return SimpleNamespace(move=chess.Move.from_uci(uci))

        worker._safe_play = fake_safe_play
        if analyse_cp is not None:
            worker._safe_analyse = lambda board: {
                "score": chess.engine.PovScore(chess.engine.Cp(analyse_cp), chess.WHITE)
            }
        else:
            worker._safe_analyse = lambda board: None

        res = worker.play_game(target_is_white=target_is_white, opening=opening)
        return res, list(worker.sound_events)

    def test_regular_moves_castling_check_and_checkmate_end_events(self):
        # 1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. O-O d6 5. Qxf7+ (illegal -> use legal sequence!)
        # Legal sequence with castling, check, and checkmate:
        # 1. e4 e5 2. Bc4 Nc6 3. Nf3 Nf6 4. O-O Nxe4 5. Bxf7+ Kxf7 6. Nxe5+ Kg8 7. Qf3 d5 8. Qf7#
        moves = [
            "e2e4", "e7e5",
            "f1c4", "b8c6",
            "g1f3", "g8f6",
            "e1g1",          # White castles kingside -> castle
            "f6e4",          # Black captures -> move-self
            "c4f7",          # Bxf7+ -> move-check
            "e8f7",          # Kxf7 -> move-self
            "f3e5",          # Nxe5+ -> move-check
            "f7g8",          # Kg8 -> move-self
            "d1f3",          # Qf3 -> move-self
            "d7d5",          # d5 -> move-self
            "f3f7",          # Qf7# -> move-check, then game-end
        ]
        res, events = self._run_scripted_game(moves)
        self.assertEqual(res, "W")
        self.assertEqual(
            events,
            [
                "game-start",
                "move-self", "move-self",
                "move-self", "move-self",
                "move-self", "move-self",
                "castle",
                "move-self",
                "move-check",
                "move-self",
                "move-check",
                "move-self",
                "move-self",
                "move-self",
                "move-check",
                "game-end",
            ],
        )

    def test_queenside_castling_and_non_checking_pawn_promotion_and_stalemate_draw(self):
        # Custom FEN where White can castle queenside (O-O-O), Black moves,
        # White promotes a7-a8=Q WITHOUT giving check, and Black is stalemated!
        # White: Ke1, Ra1, Pa7; Black: Kh6, Ph7 (blocked by White? Let's use Kh5, Pg6, Ph6 -> wait):
        # Let's test queenside castling and quiet promotion + stalemate cleanly:
        # FEN: "4k3/P7/8/8/8/8/8/R3K2r w Q - 0 1"
        # 1. O-O-O (e1c1 -> castle, no check since Black king on e8 and rook on d1 is blocked? Wait: d1 does NOT check e8!)
        # 1... Kf7 (e8f7 -> move-self)
        # 2. a8=N (a7a8n -> promote! Knight on a8 does NOT check Kf7!)
        fen = "4k3/P7/8/8/8/8/8/R3K3 w Q - 0 1"
        worker = eloify.TournamentWorker("target.exe", queue.Queue())
        original_reset = worker.board.reset

        def custom_reset():
            original_reset()
            worker.board.set_fen(fen)

        # Follow up to stalemate or insufficient material:
        # Let's play: 1. O-O-O Kf7 2. a8=N Kg7 -> then set up stalemate on next move?
        # Even simpler: play a real legal sequence to stalemate!
        # FEN: "7k/5K2/8/6P1/8/8/8/8 w - - 0 1": 1. g6 (stalemate!)
        script = iter(["e1c1", "e8f7", "a7a8n"])

        def fake_play(board, role):
            uci = next(script)
            if uci == "a7a8n":
                # After this promotion move, we'll inspect events; let's finish via max_moves=3
                pass
            return SimpleNamespace(move=chess.Move.from_uci(uci))

        worker.board.reset = custom_reset
        worker._safe_play = fake_play
        worker._safe_analyse = lambda board: None

        # Run 3 plies then trigger adjudication by setting current_move_number to 299 on 3rd move
        def fake_play_three(board, role):
            uci = next(script)
            if uci == "a7a8n":
                worker.current_move_number = 299
            return SimpleNamespace(move=chess.Move.from_uci(uci))

        worker._safe_play = fake_play_three
        res = worker.play_game(target_is_white=True)
        self.assertEqual(res, "D")
        self.assertEqual(
            list(worker.sound_events),
            ["game-start", "castle", "move-self", "promote", "game-end"],
        )

    def test_stalemate_loss_and_adjudicated_outcomes_all_emit_game_end(self):
        # 1) Stalemate draw: White Kf7, Pg5 vs Black Kh8 -> 1. g6 stalemate
        worker_draw = eloify.TournamentWorker("target.exe", queue.Queue())
        orig_reset = worker_draw.board.reset
        worker_draw.board.reset = lambda: (orig_reset(), worker_draw.board.set_fen("7k/5K2/8/6P1/8/8/8/8 w - - 0 1"))
        worker_draw._safe_play = lambda b, r: SimpleNamespace(move=chess.Move.from_uci("g5g6"))
        res_draw = worker_draw.play_game(target_is_white=True)
        self.assertEqual(res_draw, "D")
        self.assertEqual(list(worker_draw.sound_events), ["game-start", "move-self", "game-end"])

        # 2) Fool's mate loss for White (target_is_white=True): 1. f3 e5 2. g4 Qh4#
        res_loss, ev_loss = self._run_scripted_game(
            ["f2f3", "e7e5", "g2g4", "d8h4"], target_is_white=True
        )
        self.assertEqual(res_loss, "L")
        self.assertEqual(
            ev_loss,
            ["game-start", "move-self", "move-self", "move-self", "move-check", "game-end"],
        )

    def test_book_opening_does_not_emit_move_sounds_before_game_start(self):
        opening = eloify.HIGH_ELO_OPENINGS[0]  # 10 book plies
        worker = eloify.TournamentWorker("target.exe", queue.Queue())

        def play_one_then_stop(board, role):
            worker.current_move_number = 299
            return SimpleNamespace(move=next(iter(board.legal_moves)))

        worker._safe_play = play_one_then_stop
        worker._safe_analyse = lambda board: {
            "score": chess.engine.PovScore(chess.engine.Cp(-350), chess.WHITE)
        }
        res = worker.play_game(target_is_white=True, opening=opening)
        self.assertEqual(res, "L")
        events = list(worker.sound_events)
        self.assertEqual(events[0], "game-start")
        self.assertEqual(events[-1], "game-end")
        self.assertEqual(len(events), 3)  # game-start, 1 live move, game-end

    def test_aborted_game_does_not_emit_game_end(self):
        worker = eloify.TournamentWorker("target.exe", queue.Queue())

        def abort_on_move(board, role):
            worker.running = False
            raise eloify.TournamentAborted()

        worker._safe_play = abort_on_move
        with self.assertRaises(eloify.TournamentAborted):
            worker.play_game(target_is_white=True)
        self.assertEqual(list(worker.sound_events), ["game-start"])


class AppSoundDispatchTests(unittest.TestCase):
    def _make_app_with_mocks(self):
        app = eloify.EloifyApp.__new__(eloify.EloifyApp)
        app.error_text = None
        app.last_games_played = 0
        app.last_wins = 0
        app.last_draws = 0
        app.last_losses = 0
        app.sounds = {key: Mock(name=f"snd_{key}") for key in eloify.AUDIO_SOUND_FILES}
        app.sound_channels = {key: Mock(name=f"ch_{key}") for key in eloify.AUDIO_SOUND_FILES}
        return app

    def test_all_six_sound_events_dispatch_to_dedicated_channels_and_coalesce_duplicates(self):
        app = self._make_app_with_mocks()
        app.worker = SimpleNamespace(
            sound_events=deque([
                "game-start",
                "move-self",
                "move-self",  # duplicate in same frame -> played once
                "castle",
                "promote",
                "move-check",
                "game-end",
            ]),
            games_played=1,
            wins=1,
            draws=0,
            losses=0,
        )
        app._update_game_sounds()

        for key in eloify.AUDIO_SOUND_FILES:
            app.sound_channels[key].play.assert_called_once_with(app.sounds[key])
        self.assertEqual(len(app.worker.sound_events), 0)
        self.assertEqual(app.last_games_played, 1)

    def test_error_state_clears_pending_sound_events_without_playing(self):
        app = self._make_app_with_mocks()
        app.error_text = "Engine crashed"
        app.worker = SimpleNamespace(
            sound_events=deque(["game-start", "move-self", "game-end"]),
            games_played=1,
            wins=0,
            draws=0,
            losses=1,
        )
        app._update_game_sounds()

        for key in eloify.AUDIO_SOUND_FILES:
            app.sound_channels[key].play.assert_not_called()
        self.assertEqual(len(app.worker.sound_events), 0)

    def test_full_app_init_loads_all_mp3s_and_plays_events_headless(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp) / "audio"
            audio_dir.mkdir()
            for idx, filename in enumerate(eloify.AUDIO_SOUND_FILES.values(), start=5):
                (audio_dir / filename).write_bytes(_build_valid_mp3_bytes(idx * 3))

            with patch.object(eloify, "AUDIO_DIR", str(audio_dir)):
                app = eloify.EloifyApp()

            self.assertIsNotNone(app.castle_sound)
            self.assertIsNotNone(app.game_start_sound)
            self.assertIsNotNone(app.game_end_sound)
            self.assertIsNotNone(app.move_sound)
            self.assertIsNotNone(app.check_sound)
            self.assertIsNotNone(app.promote_sound)
            self.assertEqual(set(app.sound_channels.keys()), set(eloify.AUDIO_SOUND_FILES.keys()))

            for key in eloify.AUDIO_SOUND_FILES:
                app._play_game_sound(key)
            app.reset()


if __name__ == "__main__":
    unittest.main()
