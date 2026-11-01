"""Engine retry diagnostics, disk failures, and main-thread error presentation."""
import ast
from collections import deque
from datetime import datetime
import os
from pathlib import Path
import queue
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
tree = ast.parse((ROOT / "main.py").read_text())
ns = dict(chess=chess, pygame=pygame, deque=deque, datetime=datetime, os=os,
          queue=queue, re=re, tempfile=tempfile, threading=threading,
          time=time, traceback=traceback, sys=SimpleNamespace(platform="linux"),
          TIME_LIMIT=0.1, MAX_MOVE_RETRIES=10, GAMES_PER_OPPONENT=2, OPPONENTS=[],
          ADJUDICATOR_PATH="adjudicator.exe", WINDOW_WIDTH=1000, WINDOW_HEIGHT=740)
names = {"_exception_message", "_engine_failure_details", "_save_error_log",
         "_wrap_error_text", "get_engine_name", "TournamentWorker",
         "CompatibleUciProtocol", "TournamentAborted", "OpponentDead"}
nodes = [n for n in tree.body
         if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
constants = {"ERROR_REPORT_RECT", "ERROR_COPY_RECT", "ERROR_BACK_RECT"}
nodes += [n for n in tree.body if isinstance(n, ast.Assign)
          and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
app = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EloifyApp")
nodes.append(ast.ClassDef(name="ErrorApp", bases=[], keywords=[], decorator_list=[], body=[
    n for n in app.body if isinstance(n, ast.FunctionDef) and n.name in {
        "process_queue", "_copy_error_report", "handle_click", "handle_key_down",
        "handle_mouse_wheel", "_draw_error_report"}]))
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
             "main.py", "exec"), ns)


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.logs = Path(self.folder.name, "logs")
        patcher = patch.dict(ns, ERROR_LOG_DIR=str(self.logs))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.worker = ns["TournamentWorker"]("C:/引擎/engine.exe", queue.Queue(),
                                               {"time": 0.1, "threads": 4, "hash": 256})
        self.worker.target_engine = Mock(
            id={"name": "Broken engine"},
            protocol=SimpleNamespace(diagnostics=deque(["stderr: missing network.nnue"])))
        self.worker._reload_target = Mock()

    def error_payload(self):
        messages = []
        while not self.worker.queue.empty():
            messages.append(self.worker.queue.get_nowait())
        errors = [payload for kind, payload in messages if kind == "error"]
        self.assertEqual(len(errors), 1)
        return errors[0]

    def test_tenth_failure_reports_actual_errors_and_writes_full_log(self):
        self.worker.target_engine.play.side_effect = [
            chess.engine.EngineTerminatedError(f"crashed on attempt {n} (exit code: 1)")
            for n in range(1, 11)]
        self.worker.board.push_uci("e2e4")
        with self.assertRaises(ns["TournamentAborted"]):
            self.worker._safe_play(self.worker.board, "target")
        self.assertEqual(self.worker.target_engine.play.call_count, 10)
        self.assertEqual(self.worker._reload_target.call_count, 9)
        self.assertFalse(self.worker.running)
        payload = self.error_payload()
        self.assertIn("10 times", payload["summary"])
        report = payload["report"]
        self.assertIn("Last error: EngineTerminatedError: crashed on attempt 10", report)
        for n in range(1, 11):
            self.assertIn(f"Attempt {n}: EngineTerminatedError: crashed on attempt {n}", report)
        for detail in ("stderr: missing network.nnue", "Traceback (most recent call last)",
                       "Broken engine", "C:/引擎/engine.exe", "'threads': 4", "Moves (UCI): e2e4",
                       self.worker.board.fen()):
            self.assertIn(detail, report)
        self.assertIsNone(payload["log_error"])
        saved = Path(payload["log_path"]).read_text(encoding="utf-8")
        self.assertTrue(report.endswith(saved))
        self.assertIn(payload["log_path"], report)

    def test_blank_timeout_still_has_useful_message(self):
        self.worker.target_engine.play.side_effect = TimeoutError()
        with self.assertRaises(ns["TournamentAborted"]):
            self.worker._safe_play(self.worker.board, "target")
        report = self.error_payload()["report"]
        self.assertIn("TimeoutError: Engine did not respond before the command timeout.", report)

    def test_reload_failure_preserves_original_search_error(self):
        self.worker.target_engine.play.side_effect = ValueError("illegal move a1a8")
        self.worker._reload_target.side_effect = PermissionError("access denied")
        with self.assertRaises(ns["TournamentAborted"]):
            self.worker._safe_play(self.worker.board, "target")
        payload = self.error_payload()
        self.assertEqual(payload["summary"], "Could not reload target")
        self.assertIn("ValueError: illegal move a1a8", payload["report"])
        self.assertIn("PermissionError: access denied", payload["report"])

    def test_successful_retry_does_not_emit_fatal_report(self):
        move = chess.engine.PlayResult(chess.Move.from_uci("e2e4"), None)
        self.worker.target_engine.play.side_effect = [RuntimeError("transient"), move]
        self.assertIs(self.worker._safe_play(self.worker.board, "target"), move)
        self.assertFalse(self.logs.exists())
        self.assertTrue(all(kind != "error" for kind, _ in list(self.worker.queue.queue)))

    def test_startup_failure_is_also_logged(self):
        self.worker._launch_engine = Mock(side_effect=FileNotFoundError("executable missing"))
        self.worker.run()
        payload = self.error_payload()
        self.assertIn("Could not launch target", payload["summary"])
        self.assertIn("FileNotFoundError: executable missing", payload["report"])
        self.assertTrue(Path(payload["log_path"]).is_file())

    def test_read_only_install_falls_back_to_user_logs(self):
        # A file instead of a directory reliably fails even when tests run as root.
        self.logs.write_text("not a directory")
        fallback = Path(self.folder.name, "user-logs")
        with patch.object(os.path, "expanduser", return_value=str(fallback)):
            path, error = ns["_save_error_log"]("Unicode details: 引擎")
        self.assertIsNone(error)
        self.assertEqual(Path(path).parent, fallback)
        self.assertEqual(Path(path).read_text(encoding="utf-8"), "Unicode details: 引擎")

    def test_all_disk_writes_fail_but_report_still_emitted(self):
        with patch.object(os, "makedirs", side_effect=PermissionError("read-only filesystem")):
            self.worker._report_error("Engine failed", RuntimeError("real cause"))
        payload = self.error_payload()
        self.assertIsNone(payload["log_path"])
        self.assertIn("read-only filesystem", payload["log_error"])
        self.assertIn("RuntimeError: real cause", payload["report"])
        self.assertIn("Log file could not be saved", payload["report"])

    def test_reports_get_unique_files(self):
        first, _ = ns["_save_error_log"]("first")
        second, _ = ns["_save_error_log"]("second")
        self.assertNotEqual(first, second)
        self.assertEqual(Path(first).read_text(), "first")
        self.assertEqual(Path(second).read_text(), "second")


class ProtocolDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_output_and_stderr_are_captured_with_memory_bounds(self):
        protocol = ns["CompatibleUciProtocol"]()
        with patch.object(chess.engine.UciProtocol, "send_line"), \
                patch.object(chess.engine.UciProtocol, "error_line_received"):
            for n in range(100):
                protocol.line_received(f"info depth {n}")
            protocol.send_line("position startpos")
            protocol.error_line_received("failed to load network " + "x" * 5000)
        self.assertEqual(len(protocol.diagnostics), 80)
        self.assertIn(">> position startpos", protocol.diagnostics)
        self.assertTrue(protocol.diagnostics[-1].startswith("stderr: failed to load network"))
        self.assertLessEqual(len(protocol.diagnostics[-1]), 2008)


class CrashingSubprocessTests(unittest.TestCase):
    def test_stderr_and_exit_code_from_real_uci_process(self):
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder, "engine.py")
            script.write_text("""
import sys
for line in sys.stdin:
    if line.strip() == 'uci':
        print('id name Crashing fixture', flush=True)
        print('uciok', flush=True)
    elif line.strip() == 'isready':
        print('readyok', flush=True)
    elif line.startswith('go'):
        print('Cannot load required NNUE network', file=sys.stderr, flush=True)
        sys.exit(17)
""")
            with self.assertLogs("chess.engine", level="WARNING"):
                engine = chess.engine.SimpleEngine.popen(
                    ns["CompatibleUciProtocol"], [sys.executable, str(script)], timeout=2)
                try:
                    with self.assertRaises(chess.engine.EngineTerminatedError) as error:
                        engine.play(chess.Board(), chess.engine.Limit(time=0.1))
                    details = ns["_engine_failure_details"](error.exception, engine)
                    self.assertIn("exit code: 17", details)
                    self.assertIn("stderr: Cannot load required NNUE network", details)
                    self.assertIn(">> go movetime 100", details)
                finally:
                    engine.close()


class ErrorPresentationTests(unittest.TestCase):
    def setUp(self):
        self.app = ns["ErrorApp"]()
        self.app.progress_queue = queue.Queue()
        self.app.state = "RUNNING"
        self.app.error_text = None
        self.app.reset = Mock()
        self.copy = Mock(return_value=True)
        patcher = patch.dict(ns, _set_clipboard_text=self.copy)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.payload = {"summary": "Target failed 10 times", "report": "RuntimeError: actual cause\nfull history",
                        "log_path": "/logs/error.log", "log_error": None}

    def receive_error(self):
        self.app.progress_queue.put(("error", self.payload))
        self.app.process_queue()

    def test_error_auto_copies_full_report_and_survives_done(self):
        self.app.progress_queue.put(("error", self.payload))
        self.app.progress_queue.put(("done", (("estimate", 2400), (2300, 2500))))
        self.app.process_queue()
        self.assertEqual(self.app.state, "DONE")
        self.assertEqual(self.app.error_report, self.payload["report"])
        self.assertIsNone(self.app.estimated_elo)
        self.copy.assert_called_once_with(self.payload["report"])
        self.assertIn("copied", self.app.error_clipboard_status)

    def test_clipboard_failure_and_copy_button_retry(self):
        self.copy.return_value = False
        self.receive_error()
        self.assertIn("unavailable", self.app.error_clipboard_status)
        self.copy.return_value = True
        self.app.handle_click(ns["ERROR_COPY_RECT"].center)
        self.assertIn("copied", self.app.error_clipboard_status)
        self.app.reset.assert_not_called()

    def test_report_click_does_not_dismiss_error_but_back_does(self):
        self.receive_error()
        self.app.handle_click(ns["ERROR_REPORT_RECT"].center)
        self.app.reset.assert_not_called()
        self.app.handle_click(ns["ERROR_BACK_RECT"].center)
        self.app.reset.assert_called_once()

    def test_copy_shortcuts_on_windows_and_macos(self):
        self.receive_error()
        for platform, modifier in (("win32", pygame.KMOD_CTRL), ("darwin", pygame.KMOD_GUI)):
            with patch.dict(ns, sys=SimpleNamespace(platform=platform)):
                self.app.handle_key_down(SimpleNamespace(key=pygame.K_c, mod=modifier))
        self.assertEqual(self.copy.call_count, 3)

    def test_wrap_long_paths_and_scroll_error_panel(self):
        font = SimpleNamespace(size=lambda text: (len(text) * 8, 18))
        text = "Very long error\n" + "C:/" + "引擎" * 1000
        lines = ns["_wrap_error_text"](text, font, 100)
        self.assertTrue(all(font.size(line)[0] <= 100 for line in lines))
        self.assertIn("引擎", "".join(lines))
        self.receive_error()
        self.app.handle_mouse_wheel(SimpleNamespace(y=-3))
        self.assertEqual(self.app.error_scroll, 9)
        self.app.handle_mouse_wheel(SimpleNamespace(y=50))
        self.assertEqual(self.app.error_scroll, 0)


if __name__ == "__main__":
    unittest.main()
