"""Exercise engine compatibility without importing or initializing the pygame GUI."""
import ast
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import chess
import chess.engine


ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "main.py").read_text())
ns = dict(chess=chess, re=re)
names = {"CompatibleUciProtocol", "build_engine_config"}
constants = {"ENGINE_QUIT_TIMEOUT", "LEGACY_MOVETIME_GRACE"}
nodes = [n for n in tree.body
         if (isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names)
         or (isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets))]
worker = next(n for n in tree.body if isinstance(n, ast.ClassDef)
              and n.name == "TournamentWorker")
nodes.append(next(n for n in worker.body if isinstance(n, ast.FunctionDef)
                  and n.name == "_kill_engine"))
exec(compile(ast.Module(body=nodes, type_ignores=[]), "main.py", "exec"), ns)

# Respond promptly to readiness, but optionally ignore movetime or quit. Logging
# the actual commands also catches stale watchdogs that stop the next search.
FAKE_ENGINE = '''
import sys
import time
name, mode, logfile = sys.argv[1:]
for line in sys.stdin:
    line = line.strip()
    with open(logfile, "a") as log:
        log.write(line + "\\n")
    if line == "uci":
        print("id name " + name, flush=True)
        print("uciok", flush=True)
    elif line == "isready":
        print("readyok", flush=True)
    elif line.startswith("go") and mode != "overrun":
        print("bestmove e2e4", flush=True)
    elif line == "stop":
        print("bestmove e2e4", flush=True)
    elif line == "quit":
        if mode == "hang_quit":
            time.sleep(60)
        break
'''


class ConfigurationTests(unittest.TestCase):
    def test_sleeping_threads_only_when_advertised(self):
        for adjudicator in (False, True):
            engine = SimpleNamespace(options={"Use Sleeping Threads": object()})
            config = ns["build_engine_config"](engine, is_adjudicator=adjudicator)
            self.assertIs(config["Use Sleeping Threads"], True)
        self.assertEqual(ns["build_engine_config"](SimpleNamespace(options={})), {})

    def test_preserves_requested_threads_and_hash(self):
        option = SimpleNamespace(min=1, max=1024)
        engine = SimpleNamespace(options={"Threads": option, "Hash": option,
                                          "Use Sleeping Threads": object()})
        config = ns["build_engine_config"](engine, settings={"threads": 4, "hash": 256})
        self.assertEqual(config["Threads"], 4)
        self.assertEqual(config["Hash"], 256)

    def test_quit_is_bounded_and_always_closes(self):
        for error in (None, TimeoutError(), RuntimeError("dead")):
            engine = Mock(timeout=10)
            seen_timeouts = []
            def quit_engine():
                seen_timeouts.append(engine.timeout)
                if error is not None:
                    raise error
            engine.quit.side_effect = quit_engine
            ns["_kill_engine"](None, engine)
            self.assertEqual(seen_timeouts, [ns["ENGINE_QUIT_TIMEOUT"]])
            self.assertEqual(engine.timeout, 10)
            engine.close.assert_called_once()
        ns["_kill_engine"](None, None)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.script = Path(self.folder.name, "engine.py")
        self.script.write_text(FAKE_ENGINE)
        self.log = Path(self.folder.name, "commands.txt")

    def launch(self, name, mode):
        engine = chess.engine.SimpleEngine.popen(
            ns["CompatibleUciProtocol"],
            [sys.executable, str(self.script), name, mode, str(self.log)], timeout=2)
        self.addCleanup(engine.close)
        return engine

    def test_legacy_overrun_stopped_for_each_search(self):
        for name in ("Stockfish 2.2 64bit", "Stockfish 2.2.2 64bit SSE4.2"):
            with self.subTest(name=name):
                engine = self.launch(name, "overrun")
                for _ in range(2):
                    start = time.monotonic()
                    result = engine.play(chess.Board(), chess.engine.Limit(time=0.05))
                    elapsed = time.monotonic() - start
                    self.assertEqual(result.move, chess.Move.from_uci("e2e4"))
                    self.assertGreaterEqual(elapsed, 0.05)
                    self.assertLess(elapsed, 1.5)
                engine.quit()
        commands = self.log.read_text().splitlines()
        self.assertEqual(commands.count("go movetime 50"), 4)
        self.assertEqual(commands.count("stop"), 4)

    def test_early_bestmove_cancels_watchdog(self):
        engine = self.launch("Stockfish 2.2.2 64bit SSE4.2", "early")
        engine.play(chess.Board(), chess.engine.Limit(time=0.02))
        time.sleep(0.25)  # Past the old watchdog deadline.
        engine.ping()
        self.assertNotIn("stop", self.log.read_text().splitlines())
        engine.quit()

    def test_unaffected_engines_have_no_watchdog(self):
        for name in ("Stockfish 19", "Stockfish 2.3", "Stockfish 2.20", "Other 2.2"):
            engine = self.launch(name, "overrun")
            analysis = engine.analysis(chess.Board(), chess.engine.Limit(time=0.02))
            self.assertIsNone(engine.protocol._movetime_stop)
            analysis.stop()
            analysis.wait()
            engine.quit()

    def test_depth_only_search_has_no_watchdog(self):
        engine = self.launch("Stockfish 2.2.2 64bit SSE4.2", "overrun")
        analysis = engine.analysis(chess.Board(), chess.engine.Limit(depth=5))
        self.assertIsNone(engine.protocol._movetime_stop)
        analysis.stop()
        analysis.wait()
        engine.quit()

    def test_shutdown_kills_engine_that_ignores_quit(self):
        engine = self.launch("Stockfish 1.5.1 JA", "hang_quit")
        start = time.monotonic()
        ns["_kill_engine"](None, engine)
        self.assertLess(time.monotonic() - start, 2.5)
        self.assertIsNotNone(engine.returncode.result(timeout=2))

    def test_quit_cancels_pending_watchdog(self):
        engine = self.launch("Stockfish 2.2", "overrun")
        # Send a search without an analysis command owning the response: this
        # tests quit cancellation without python-chess's unrelated outstanding
        # analysis-command futures on engine termination.
        import asyncio
        async def start_search():
            engine.protocol.send_line("position startpos")
            engine.protocol.send_line("go movetime 500")
            self.assertIsNotNone(engine.protocol._movetime_stop)
        asyncio.run_coroutine_threadsafe(start_search(), engine.protocol.loop).result(timeout=2)
        ns["_kill_engine"](None, engine)
        self.assertIsNone(engine.protocol._movetime_stop)
        self.assertIsNotNone(engine.returncode.result(timeout=2))


if __name__ == "__main__":
    unittest.main()
