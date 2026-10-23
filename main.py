import pygame
import chess
import chess.engine
import threading
import queue
import time
import math
import os
import sys
import subprocess
import random
import array

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
FOX_CHESS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines", "fox-chess")

ADJUDICATOR_PATH = r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Stockfish 19\stockfish\stockfish-windows-x86-64-universal.exe"

OPPONENTS = [
    # --- Stockfish 1.x ---
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.0\stockfish_x64.exe",                                   2400),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.1\stockfish_11_x64_ja.exe",                             2470),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.1a\stockfish_11a_x64_ja.exe",                           2480),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.3\stockfish_13_x64_ja.exe",                             2550),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.3.1\stockfish_131_x64_ja.exe",                          2560),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.4\stockfish_14_x64_ja.exe",                             2620),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.5\stockfish_15_x64_ja.exe",                             2700),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.5.1\stockfish_151_ja.exe",                              2710),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.6\stockfish-16-x64-ja.exe",                             2720),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.6.2\stockfish-162-x64-ja.exe",                          2735),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.7\Windows\stockfish-17-64-ja.exe",                      2745),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.7.1\Windows\stockfish-171-64-ja.exe",                   2750),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.8\Windows\stockfish-18-64-ja.exe",                      2800),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.9\Windows\stockfish-19-64-ja.exe",                      2830),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 1.9.1\Windows\stockfish-191-64-ja.exe",                   2840),
    # --- Stockfish 2.x ---
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.0\Windows\stockfish-20-64-ja.exe",                      2850),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.0.1\Windows\stockfish-201-64-ja.exe",                   2870),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.1\Windows\stockfish-21-64-ja.exe",                      2900),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.2\Windows\stockfish-22-64-ja.exe",                      2920),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.2.2\Windows\64\Gcc\stockfish-222-sse42-ja.exe",        2930),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.3\Windows\stockfish-23-64-sse42-ja.exe",                2940),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 2.3.1\Windows\stockfish-231-64-popcnt-ja.exe",            2945),
    # --- Stockfish 3+ ---
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 3\Windows\AMD 64\stockfish-3-64-pop-ja.exe",              2950),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 4\Windows\stockfish_4_x64_modern_sse42.exe",              3050),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 5\Windows\stockfish_14053109_x64_modern.exe",             3120),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish DD\Windows\stockfish-dd-64-modern.exe",                   3150),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 6\Windows\stockfish-6-bmi2.exe",                          3200),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 7\Windows\stockfish 7 x64 bmi2.exe",                      3260),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 8\Windows\stockfish_8_x64_bmi2.exe",                      3320),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 9\Windows\stockfish_9_x64_bmi2.exe",                      3400),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 10\Windows\stockfish_10_x64_bmi2.exe",                    3480),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 11\Windows\stockfish_20011801_x64_bmi2.exe",              3495),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 12\stockfish_20090216_x64_avx2.exe",                      3505),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 13\stockfish_13_win_x64_avx2.exe",                        3520),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 14\stockfish_14_x64_avx2.exe",                            3535),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 14.1\stockfish_14.1_win_x64_avx2.exe",                    3540),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 15\stockfish_15_x64_avx2.exe",                            3545),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 15.1\stockfish-windows-2022-x86-64-avx2.exe",             3550),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 16\stockfish-windows-x86-64-avx2.exe",                    3560),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 16.1\stockfish-windows-x86-64-avx2.exe",                  3570),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 17\stockfish-windows-x86-64-avx2.exe",                    3585),
    (r"C:\Users\Blake\Documents\_Engines\Chess\Stockfish\Stockfish 17.1\stockfish-windows-x86-64-avx2.exe",                  3595),
    # --- Custom Eloify test builds ---
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Stockfish 18\stockfish\stockfish-windows-x86-64-avx2.exe",        3620),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Stockfish 19\stockfish\stockfish-windows-x86-64-universal.exe",   3660),
    # --- Other engines ---
    (os.path.join(FOX_CHESS_DIR, "v1.0-avx2-bmi2.exe"), 2740),
    (os.path.join(FOX_CHESS_DIR, "v1.1-avx2-bmi2.exe"), 2870),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\RandomMover\chess-random-mover.exe",                               300),
    # --- Maia v1 (lc0-based, human-like play; NPS forced to 1) ---
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1100.bat",                              1100),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1200.bat",                              1200),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1300.bat",                              1300),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1400.bat",                              1400),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1500.bat",                              1500),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1600.bat",                              1600),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1700.bat",                              1700),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1800.bat",                              1800),
    (r"C:\Users\Blake\Documents\_Projects\E\Eloify\engines\Maia and Lc0\Maia v1\maia-1900.bat",                              1900),
]

GAMES_PER_OPPONENT = 2
TIME_LIMIT = 0.1

MAX_MOVE_RETRIES = 10

# ----------------------------------------------------------------------
# UI CONSTANTS  — refined palette
# ----------------------------------------------------------------------
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 740
FPS = 60

BACKGROUND   = (22, 24, 30)
PANEL        = (34, 38, 48)
PANEL_HOVER  = (46, 52, 66)
BORDER       = (60, 66, 80)
TEXT_COLOR   = (225, 228, 235)
DIM_TEXT     = (140, 148, 165)
ACCENT       = (100, 200, 160)
GOLD         = (255, 210, 90)
ERROR_COLOR  = (230, 110, 110)
WIN_COLOR    = (120, 210, 130)
LOSS_COLOR   = (230, 110, 110)
DRAW_COLOR   = (180, 185, 195)

BOARD_SIZE = 480
SQUARE_SIZE = BOARD_SIZE // 8
BOARD_POS = (30, 140)
INFO_POS = (540, 140)

BOARD_LIGHT = (238, 216, 183)
BOARD_DARK  = (171, 122, 89)

MOVE_ANIM_DURATION = 0.10

REVEAL_DURATION = 2.0
ELO_POP_DURATION = 0.7

# Settings sliders — (key, label, min, max, step, kind)
SLIDER_CONFIGS = [
    ("cpu_cores", "CPU Cores",              1,   64,   1,    "int"),
    ("threads",   "Threads per Engine",     1,   128,  1,    "int"),
    ("hash",      "Hash per Engine (MB)",   16,  8192, 16,   "int"),
    ("time",      "Time per Move (s)",      0.01, 10.0, 0.01, "float"),
]

# Browse dialog layout
BROWSE_PANEL         = pygame.Rect(50, 60, 900, 620)
BROWSE_FIELD         = pygame.Rect(80, 120, 840, 38)
BROWSE_UP_RECT       = pygame.Rect(80, 172, 60, 30)
BROWSE_HOME_RECT     = pygame.Rect(148, 172, 72, 30)
BROWSE_REFRESH_RECT  = pygame.Rect(228, 172, 84, 30)
BROWSE_LIST          = pygame.Rect(80, 214, 840, 356)
BROWSE_INFO_Y        = 582
BROWSE_CANCEL_RECT   = pygame.Rect(740, 612, 90, 38)
BROWSE_OPEN_RECT     = pygame.Rect(840, 612, 90, 38)
BROWSE_ROW_HEIGHT    = 24
BROWSE_FIELD_PADDING = 8

SELECTION_BG   = (55, 95, 135)
FIELD_BG       = (20, 24, 30)
FIELD_BORDER   = (70, 76, 90)
LIST_BG        = (26, 30, 38)
LIST_ROW_HOVER = (40, 46, 56)
LIST_ROW_SEL   = (50, 90, 70)

# ----------------------------------------------------------------------
# EXCEPTIONS
# ----------------------------------------------------------------------
class OpponentDead(Exception):
    pass

class TournamentAborted(Exception):
    pass

# ----------------------------------------------------------------------
# CLIPBOARD (cross-platform, no tkinter)
# ----------------------------------------------------------------------
def _get_clipboard_text():
    if sys.platform == "win32":
        try:
            import ctypes
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            if not user32.OpenClipboard(None):
                raise RuntimeError("OpenClipboard failed")
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if not handle:
                    return ""
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return ""
                try:
                    return ctypes.wstring_at(ptr)
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except Exception:
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                    capture_output=True, text=True, timeout=2,
                )
                return result.stdout.rstrip("\r\n")
            except Exception:
                return ""
    elif sys.platform == "darwin":
        try:
            return subprocess.check_output(
                ["pbpaste"], stderr=subprocess.DEVNULL
            ).decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        for cmd in (["xclip", "-selection", "clipboard", "-o"],
                    ["xsel", "-b", "-o"]):
            try:
                return subprocess.check_output(
                    cmd, stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
            except Exception:
                continue
        return ""

def _set_clipboard_text(text):
    if sys.platform == "win32":
        try:
            import ctypes
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            data = text.encode("utf-16-le") + b"\x00\x00"
            if not user32.OpenClipboard(None):
                return False
            try:
                user32.EmptyClipboard()
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                if not h:
                    return False
                ptr = kernel32.GlobalLock(h)
                if not ptr:
                    return False
                try:
                    ctypes.memmove(ptr, data, len(data))
                finally:
                    kernel32.GlobalUnlock(h)
                user32.SetClipboardData(CF_UNICODETEXT, h)
                return True
            finally:
                user32.CloseClipboard()
        except Exception:
            return False
    elif sys.platform == "darwin":
        try:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
            return True
        except Exception:
            return False
    else:
        for cmd in (["xclip", "-selection", "clipboard"],
                    ["xsel", "-b", "-i"]):
            try:
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"))
                return True
            except Exception:
                continue
        return False

# ----------------------------------------------------------------------
# TEXT FIELD (editable single-line input with cursor/selection)
# ----------------------------------------------------------------------
class TextField:
    def __init__(self, text=""):
        self.text = text
        self.cursor = len(text)
        self.sel_start = None
        self.sel_end = None
        self.scroll = 0

    def set_text(self, s):
        self.text = s
        self.cursor = len(s)
        self.clear_selection()
        self.scroll = 0

    def has_selection(self):
        return (self.sel_start is not None and self.sel_end is not None
                and self.sel_start != self.sel_end)

    def get_selection_range(self):
        if not self.has_selection():
            return None
        return (min(self.sel_start, self.sel_end),
                max(self.sel_start, self.sel_end))

    def clear_selection(self):
        self.sel_start = None
        self.sel_end = None

    def select_all(self):
        self.sel_start = 0
        self.sel_end = len(self.text)
        self.cursor = len(self.text)

    def delete_selection(self):
        rng = self.get_selection_range()
        if rng is None:
            return False
        a, b = rng
        self.text = self.text[:a] + self.text[b:]
        self.cursor = a
        self.clear_selection()
        return True

    def insert(self, s):
        self.delete_selection()
        self.text = self.text[:self.cursor] + s + self.text[self.cursor:]
        self.cursor += len(s)

    def backspace(self):
        if self.delete_selection():
            return
        if self.cursor > 0:
            self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
            self.cursor -= 1

    def delete(self):
        if self.delete_selection():
            return
        if self.cursor < len(self.text):
            self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]

    def move_cursor(self, delta, shift=False):
        if shift:
            if self.sel_start is None:
                self.sel_start = self.cursor
            self.cursor = max(0, min(len(self.text), self.cursor + delta))
            self.sel_end = self.cursor
        else:
            self.cursor = max(0, min(len(self.text), self.cursor + delta))
            self.clear_selection()

    def move_home(self, shift=False):
        if shift:
            if self.sel_start is None:
                self.sel_start = self.cursor
            self.cursor = 0
            self.sel_end = self.cursor
        else:
            self.cursor = 0
            self.clear_selection()

    def move_end(self, shift=False):
        if shift:
            if self.sel_start is None:
                self.sel_start = self.cursor
            self.cursor = len(self.text)
            self.sel_end = self.cursor
        else:
            self.cursor = len(self.text)
            self.clear_selection()

# ----------------------------------------------------------------------
# ELO ESTIMATION
# ----------------------------------------------------------------------
def estimate_elo_vs_pool(per_opponent):
    total_score = sum(w + 0.5 * d for (_, w, d, l) in per_opponent)
    total_games = sum(w + d + l for (_, w, d, l) in per_opponent)
    if total_games == 0:
        return None

    def expected_total(target_elo):
        s = 0.0
        for opp_rating, w, d, l in per_opponent:
            n = w + d + l
            p = 1.0 / (1.0 + 10.0 ** ((opp_rating - target_elo) / 400.0))
            s += p * n
        return s

    if total_score >= total_games - 1e-9:
        return ("lower_bound", max(r for (r, _, _, _) in per_opponent) + 400)
    if total_score <= 1e-9:
        return ("upper_bound", min(r for (r, _, _, _) in per_opponent) - 400)

    lo, hi = 0.0, 5000.0
    while hi - lo > 0.5:
        mid = (lo + hi) / 2.0
        if expected_total(mid) < total_score:
            lo = mid
        else:
            hi = mid
    return ("ok", (lo + hi) / 2.0)

def confidence_interval_95(per_opponent):
    total_games = sum(w + d + l for (_, w, d, l) in per_opponent)
    total_score = sum(w + 0.5 * d for (_, w, d, l) in per_opponent)
    if total_games == 0:
        return None
    p = total_score / total_games
    if p <= 0.001 or p >= 0.999:
        return None
    se = 400.0 / (math.log(10.0) * math.sqrt(total_games * p * (1.0 - p)))
    return 1.96 * se

# ----------------------------------------------------------------------
# SYSTEM RESOURCE DETECTION
# ----------------------------------------------------------------------
def _detect_total_ram_mb():
    try:
        import psutil
        return psutil.virtual_memory().total // (1024 * 1024)
    except ImportError:
        pass
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) // 1024
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return stat.ullTotalPhys // (1024 * 1024)
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"], stderr=subprocess.DEVNULL
            ).strip()
            return int(out) // (1024 * 1024)
        except Exception:
            pass
    return None

def get_recommended_hash_mb(is_adjudicator=False):
    total = _detect_total_ram_mb()
    if total is None:
        return 512
    return max(128, min(total // (4 if is_adjudicator else 8), 4096))

def get_recommended_threads(is_adjudicator=False, cpu_cores=None):
    cpu = cpu_cores if cpu_cores is not None else (os.cpu_count() or 4)
    return max(1, cpu if is_adjudicator else cpu // 2)

# ----------------------------------------------------------------------
# MAIA DETECTION
# ----------------------------------------------------------------------
def is_maia_engine(engine, path=None):
    try:
        name = (engine.id or {}).get("name", "") if engine.id else ""
    except Exception:
        name = ""
    if name and "maia" in name.lower():
        return True
    if path:
        base = os.path.basename(path).lower()
        if "maia" in base:
            return True
        parent = os.path.dirname(path).lower()
        if "maia" in parent:
            return True
    return False

# ----------------------------------------------------------------------
# UCI ENGINE CONFIGURATION
# ----------------------------------------------------------------------
def build_engine_config(engine, is_adjudicator=False, path=None, settings=None):
    opts = engine.options
    s = {}
    settings = settings or {}

    if "Threads" in opts:
        t = settings.get("threads")
        if t is None:
            t = get_recommended_threads(is_adjudicator)
        try:
            if opts["Threads"].max is not None:
                t = min(t, opts["Threads"].max)
            if opts["Threads"].min is not None:
                t = max(t, opts["Threads"].min)
        except Exception:
            pass
        s["Threads"] = max(1, t)
    if "Hash" in opts:
        h = settings.get("hash")
        if h is None:
            h = get_recommended_hash_mb(is_adjudicator)
        try:
            if opts["Hash"].max is not None:
                h = min(h, opts["Hash"].max)
            if opts["Hash"].min is not None:
                h = max(h, opts["Hash"].min)
        except Exception:
            pass
        s["Hash"] = h
    if "Skill Level" in opts:
        try:
            s["Skill Level"] = opts["Skill Level"].max
        except Exception:
            pass
    if "UCI_LimitStrength" in opts:
        s["UCI_LimitStrength"] = False
    if "Strength" in opts:
        try:
            s["Strength"] = opts["Strength"].max
        except Exception:
            pass
    if "Ponder" in opts:
        s["Ponder"] = False
    if "MultiPV" in opts:
        s["MultiPV"] = 1

    if not is_adjudicator and path is not None and is_maia_engine(engine, path):
        s["NodesPerSecond"] = 1

    return s

def apply_engine_config(engine, settings):
    if not settings:
        return
    try:
        engine.configure(settings)
    except Exception:
        for k, v in settings.items():
            try:
                engine.configure({k: v})
            except Exception:
                pass

def get_engine_name(engine, fallback="Unknown"):
    try:
        if engine.id and "name" in engine.id:
            return engine.id["name"]
    except Exception:
        pass
    return fallback

def format_config(settings):
    parts = []
    if "Threads" in settings:
        parts.append(f"T={settings['Threads']}")
    if "Hash" in settings:
        parts.append(f"H={settings['Hash']}MB")
    if "NodesPerSecond" in settings:
        parts.append(f"NPS={settings['NodesPerSecond']}")
    if "Skill Level" in settings:
        parts.append(f"Skill={settings['Skill Level']}")
    if "Strength" in settings:
        parts.append(f"Str={settings['Strength']}")
    return ", ".join(parts) if parts else "default"

# ----------------------------------------------------------------------
# SOUND SYNTHESIS
# ----------------------------------------------------------------------
def _generate_drumroll(duration=REVEAL_DURATION, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    sparkle_scale = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.50, 1174.66, 1318.51]
    note_count = len(sparkle_scale)
    note_spacing = (duration - 0.4) / note_count

    for i in range(n):
        t = i / sr
        progress = t / duration
        val = 0.0
        pad_freq = 110.0 + 110.0 * progress
        pad_env = min(1.0, t / 0.4) * (0.45 + 0.55 * progress)
        if t > duration - 0.2:
            pad_env *= max(0.0, (duration - t) / 0.2)
        val += math.sin(2 * math.pi * pad_freq * t) * pad_env * 0.08
        val += math.sin(2 * math.pi * pad_freq * 2 * t) * pad_env * 0.04
        val += math.sin(2 * math.pi * pad_freq * 3 * t) * pad_env * 0.02
        for idx, freq in enumerate(sparkle_scale):
            start = 0.15 + idx * note_spacing
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.01)
                env = attack * math.exp(-dt * 3.2)
                vib = math.sin(2 * math.pi * 5.5 * dt) * 0.004
                phase = 2 * math.pi * freq * (1 + vib) * dt
                val += math.sin(phase) * env * 0.10
                val += math.sin(phase * 2) * env * 0.03
        noise_vol = (progress ** 2) * 0.04 * (1.0 - progress * 0.5)
        val += (random.random() * 2 - 1) * noise_vol
        if t > duration - 0.3:
            ct = (t - (duration - 0.3)) / 0.3
            for f in (1046.50, 1318.51, 1567.98):
                val += math.sin(2 * math.pi * f * t) * ct * 0.04
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 26000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_celebration(duration=1.6, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    arpeggio = [(0.00, 523.25), (0.07, 659.25), (0.14, 783.99)]
    chord_start = 0.22
    chord_freqs = [523.25, 659.25, 783.99, 1046.50]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in arpeggio:
            if t >= start:
                dt = t - start
                env = math.exp(-dt * 4.0) * 0.4
                if dt < 0.01:
                    env *= dt / 0.01
                val += math.sin(2 * math.pi * freq * t) * env
        if t >= chord_start:
            dt = t - chord_start
            env = math.exp(-dt * 2.0) * 0.5
            if dt < 0.02:
                env *= dt / 0.02
            for freq in chord_freqs:
                val += math.sin(2 * math.pi * freq * t) * env / len(chord_freqs)
        val += (random.random() * 2 - 1) * 0.05 * math.exp(-t * 3.0)
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 28000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_move_sound(duration=0.05, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    for i in range(n):
        t = i / sr
        env = math.exp(-t * 90)
        val = math.sin(2 * math.pi * 620 * t) * env * 0.55
        val += math.sin(2 * math.pi * 260 * t) * env * 0.25
        samples[i] = int(max(-1.0, min(1.0, val)) * 12000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_capture_sound(duration=0.09, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    for i in range(n):
        t = i / sr
        env = math.exp(-t * 40)
        val = (random.random() * 2 - 1) * 0.7 * env
        val += math.sin(2 * math.pi * 180 * t) * env * 0.35
        samples[i] = int(max(-1.0, min(1.0, val)) * 14000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_check_sound(duration=0.4, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    for i in range(n):
        t = i / sr
        val = 0.0
        env1 = math.exp(-t * 14)
        val += math.sin(2 * math.pi * 1318.51 * t) * env1 * 0.35
        val += math.sin(2 * math.pi * 2637.02 * t) * env1 * 0.08
        if t >= 0.10:
            dt = t - 0.10
            attack = min(1.0, dt / 0.008)
            env2 = attack * math.exp(-dt * 12)
            val += math.sin(2 * math.pi * 987.77 * dt) * env2 * 0.35
            val += math.sin(2 * math.pi * 1975.53 * dt) * env2 * 0.08
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 18000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_checkmate_sound(duration=1.6, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    gong_partials = [(1.0, 1.0, 1.2), (2.7, 0.6, 2.0), (4.2, 0.4, 2.5),
                     (5.4, 0.3, 3.0), (7.1, 0.2, 3.5)]
    base_freq = 110.0
    fall_notes = [(0.0, 392.00), (0.20, 349.23), (0.40, 261.63)]
    for i in range(n):
        t = i / sr
        val = 0.0
        gong_attack = min(1.0, t / 0.005)
        for ratio, amp, decay in gong_partials:
            env = gong_attack * math.exp(-t * decay)
            val += math.sin(2 * math.pi * base_freq * ratio * t) * env * amp * 0.14
        for start, freq in fall_notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.02)
                env = attack * math.exp(-dt * 2.0)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.18
                val += math.sin(2 * math.pi * freq * 1.005 * dt) * env * 0.09
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 24000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_win_sound(duration=1.0, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 523.25), (0.09, 659.25), (0.18, 783.99), (0.27, 1046.50)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.01)
                env = attack * math.exp(-dt * 3.0)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.30
                val += math.sin(2 * math.pi * freq * 2 * dt) * env * 0.07
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 22000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_loss_sound(duration=1.0, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 392.00), (0.22, 311.13), (0.44, 261.63)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.02)
                env = attack * math.exp(-dt * 2.2)
                vib = math.sin(2 * math.pi * 5.5 * dt) * 0.01
                val += math.sin(2 * math.pi * freq * (1 + vib) * dt) * env * 0.28
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 21000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

def _generate_draw_sound(duration=0.7, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 523.25), (0.18, 698.46)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.015)
                env = attack * math.exp(-dt * 3.5)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.25
                val += math.sin(2 * math.pi * freq * 2 * dt) * env * 0.05
        val = max(-1.0, min(1.0, val))
        samples[i] = int(val * 20000)
    return pygame.mixer.Sound(buffer=samples.tobytes())

# ----------------------------------------------------------------------
# EASING
# ----------------------------------------------------------------------
def ease_out_back(t, s=3.0):
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2

# ----------------------------------------------------------------------
# FONT / TEXT CACHING
# ----------------------------------------------------------------------
_FONT_CACHE = {}
_FONT_FAMILY = "Arial"

def _init_font_family():
    global _FONT_FAMILY
    for name in ["Segoe UI", "Roboto", "Helvetica Neue", "Helvetica", "Arial"]:
        try:
            if pygame.font.match_font(name):
                _FONT_FAMILY = name
                return
        except Exception:
            continue

def _get_font(name, size, bold=False):
    key = (name, size, bold)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = pygame.font.SysFont(name, size, bold=bold)
        _FONT_CACHE[key] = f
    return f

_TEXT_CACHE = {}
def _render_text(text, size, color, bold):
    key = (text, size, color, bold)
    surf = _TEXT_CACHE.get(key)
    if surf is None:
        if len(_TEXT_CACHE) > 600:
            _TEXT_CACHE.clear()
        surf = _get_font(_FONT_FAMILY, size, bold).render(text, True, color)
        _TEXT_CACHE[key] = surf
    return surf

def draw_text(surface, text, pos, size=24, color=TEXT_COLOR, bold=False):
    surface.blit(_render_text(text, size, color, bold), pos)

def draw_text_centered(surface, text, center, size=24, color=TEXT_COLOR, bold=False):
    surf = _render_text(text, size, color, bold)
    surface.blit(surf, surf.get_rect(center=center))

def draw_section(surface, title, pos, width=150):
    draw_text(surface, title, pos, 15, ACCENT, bold=True)
    y = pos[1] + 19
    pygame.draw.line(surface, BORDER, (pos[0], y), (pos[0] + width, y), 1)

def draw_rounded_panel(surface, rect, fill=PANEL, border=BORDER, radius=8):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)

# ----------------------------------------------------------------------
# PIECE FONT / SURFACE CACHING
# ----------------------------------------------------------------------
_PIECE_FONT_CACHE = {}
PIECE_GLYPHS = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

def _glyph_renders(font, char):
    try:
        real = font.render(char, True, (0, 0, 0))
        if real.get_width() == 0 or real.get_height() == 0:
            return False
        tofu = font.render("\uE000", True, (0, 0, 0))
        if real.get_size() != tofu.get_size():
            return True
        to_bytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
        return to_bytes(real, "RGBA") != to_bytes(tofu, "RGBA")
    except Exception:
        return False

def _get_piece_font(size):
    if size in _PIECE_FONT_CACHE:
        return _PIECE_FONT_CACHE[size]
    for name in ["Segoe UI Symbol", "DejaVu Sans", "Arial Unicode MS",
                 "Noto Sans Symbols 2", "FreeSerif"]:
        try:
            f = pygame.font.SysFont(name, size)
            if _glyph_renders(f, "♔") and _glyph_renders(f, "♟"):
                _PIECE_FONT_CACHE[size] = f
                return f
        except Exception:
            continue
    f = pygame.font.SysFont("Arial", size)
    _PIECE_FONT_CACHE[size] = f
    return f

_PIECE_SURFACE_CACHE = {}
def _get_piece_surface(symbol, size):
    key = (symbol, size)
    surf = _PIECE_SURFACE_CACHE.get(key)
    if surf is not None:
        return surf
    font = _get_piece_font(size)
    glyph = PIECE_GLYPHS[symbol]
    text = font.render(glyph, True, (0, 0, 0))
    shadow = font.render(glyph, True, (40, 40, 40))
    w, h = text.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    out.blit(shadow, (1, 1))
    out.blit(text, (0, 0))
    _PIECE_SURFACE_CACHE[key] = out
    return out

def _sq_to_center_px(square, pos):
    row = 7 - (square // 8)
    col = square % 8
    return (pos[0] + col * SQUARE_SIZE + SQUARE_SIZE // 2,
            pos[1] + row * SQUARE_SIZE + SQUARE_SIZE // 2)

def _draw_piece_at(surface, symbol, cx, cy):
    size = int(SQUARE_SIZE * 0.85)
    surf = _get_piece_surface(symbol, size)
    surface.blit(surf, surf.get_rect(center=(cx, cy)))

# ----------------------------------------------------------------------
# BOARD BACKGROUND + LAST-MOVE HIGHLIGHT CACHES
# ----------------------------------------------------------------------
_BOARD_BG_CACHE = {}
def _get_board_bg(size):
    surf = _BOARD_BG_CACHE.get(size)
    if surf is not None:
        return surf
    sq = size // 8
    surf = pygame.Surface((size, size)).convert()
    coord_font = _get_font(_FONT_FAMILY, max(10, sq // 5), bold=True)
    for row in range(8):
        for col in range(8):
            is_light = (row + col) % 2 == 0
            color = BOARD_LIGHT if is_light else BOARD_DARK
            rect = pygame.Rect(col * sq, row * sq, sq, sq)
            pygame.draw.rect(surf, color, rect)
            pygame.draw.rect(surf, tuple(max(0, c - 18) for c in color),
                             rect, width=1)
            coord_color = BOARD_DARK if is_light else BOARD_LIGHT
            if col == 0:
                rank = str(8 - row)
                s = coord_font.render(rank, True, coord_color)
                surf.blit(s, (col * sq + 3, row * sq + 2))
            if row == 7:
                file_letter = chr(ord('a') + col)
                s = coord_font.render(file_letter, True, coord_color)
                surf.blit(s, (col * sq + sq - s.get_width() - 3,
                              row * sq + sq - s.get_height() - 2))
    _BOARD_BG_CACHE[size] = surf
    return surf

_LAST_MOVE_HL = None
def _get_last_move_highlight():
    global _LAST_MOVE_HL
    if _LAST_MOVE_HL is None:
        s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
        s.fill((255, 220, 100, 72))
        _LAST_MOVE_HL = s
    return _LAST_MOVE_HL

_BOARD_FEN_CACHE = {}
def _get_board(fen):
    if len(_BOARD_FEN_CACHE) > 200:
        _BOARD_FEN_CACHE.clear()
    b = _BOARD_FEN_CACHE.get(fen)
    if b is None:
        b = chess.Board(fen)
        _BOARD_FEN_CACHE[fen] = b
    return b

# ----------------------------------------------------------------------
# MOVE ANIMATION
# ----------------------------------------------------------------------
class MoveAnimation:
    def __init__(self, from_sq, to_sq, rook_from=None, rook_to=None,
                 captured_square=None, captured_symbol=None,
                 duration=MOVE_ANIM_DURATION):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.rook_from = rook_from
        self.rook_to = rook_to
        self.captured_square = captured_square
        self.captured_symbol = captured_symbol
        self.start = time.time()
        self.duration = duration

    def progress(self):
        return min(1.0, max(0.0, (time.time() - self.start) / self.duration))

    def done(self):
        return self.progress() >= 1.0

def draw_board(surface, board_fen, pos, animation=None, last_move=None):
    board = _get_board(board_fen)
    surface.blit(_get_board_bg(BOARD_SIZE), pos)
    if last_move is not None:
        hl = _get_last_move_highlight()
        for sq in last_move:
            if sq is None:
                continue
            row = 7 - (sq // 8)
            col = sq % 8
            surface.blit(hl, (pos[0] + col * SQUARE_SIZE,
                              pos[1] + row * SQUARE_SIZE))
    animating = animation is not None and not animation.done()
    skip = set()
    if animating:
        skip.add(animation.to_sq)
        if animation.rook_to is not None:
            skip.add(animation.rook_to)
        if animation.captured_square is not None:
            skip.add(animation.captured_square)
    for square in chess.SQUARES:
        if square in skip:
            continue
        piece = board.piece_at(square)
        if not piece:
            continue
        cx, cy = _sq_to_center_px(square, pos)
        _draw_piece_at(surface, piece.symbol(), cx, cy)
    if animating:
        t = animation.progress()
        if animation.captured_square is not None and animation.captured_symbol is not None:
            cx, cy = _sq_to_center_px(animation.captured_square, pos)
            _draw_piece_at(surface, animation.captured_symbol, cx, cy)
        moved = board.piece_at(animation.to_sq)
        if moved:
            fx, fy = _sq_to_center_px(animation.from_sq, pos)
            tx, ty = _sq_to_center_px(animation.to_sq, pos)
            _draw_piece_at(surface, moved.symbol(),
                           fx + (tx - fx) * t, fy + (ty - fy) * t)
        if animation.rook_to is not None:
            rook = board.piece_at(animation.rook_to)
            if rook:
                fx, fy = _sq_to_center_px(animation.rook_from, pos)
                tx, ty = _sq_to_center_px(animation.rook_to, pos)
                _draw_piece_at(surface, rook.symbol(),
                               fx + (tx - fx) * t, fy + (ty - fy) * t)

# ----------------------------------------------------------------------
# TOURNAMENT WORKER
# ----------------------------------------------------------------------
class TournamentWorker(threading.Thread):
    def __init__(self, target_path, progress_queue, settings=None):
        super().__init__(daemon=True)
        self.target_path = target_path
        self.queue = progress_queue
        self.settings = settings or {}
        self.board = chess.Board()
        self.running = True
        self.total_games = GAMES_PER_OPPONENT * len(OPPONENTS)
        self.games_played = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.current_fen_shared = chess.STARTING_FEN
        self.target_name = "…"
        self.opponent_name = "…"
        self.opponent_rating = 0
        self.target_config_str = ""
        self.opponent_config_str = ""
        self.last_move_san = ""
        self.last_move_uci = ""
        self.total_move_counter = 0
        self.current_move_number = 0
        self.target_is_white = True
        self.recent_moves = []
        self.last_game_result = ""
        self.last_game_was_checkmate = False
        self.current_opponent_index = 0
        self.per_opponent_results = []
        self.target_engine = None
        self.opponent_engine = None
        self.adjudicator_engine = None
        self.current_opponent_path = None
        self.opponent_reloaded = False

    def _launch_engine(self, path, is_adjudicator=False):
        eng = chess.engine.SimpleEngine.popen_uci(path)
        cfg = build_engine_config(eng, is_adjudicator=is_adjudicator,
                                  path=path, settings=self.settings)
        apply_engine_config(eng, cfg)
        return eng

    def _kill_engine(self, eng):
        if eng is None:
            return
        try:
            eng.quit()
        except Exception:
            pass
        try:
            eng.close()
        except Exception:
            pass

    def _reload_target(self):
        self.queue.put(("status", "Reloading target engine…"))
        self._kill_engine(self.target_engine)
        self.target_engine = self._launch_engine(self.target_path, is_adjudicator=False)
        try:
            name = get_engine_name(self.target_engine, self.target_name)
            if name:
                self.target_name = name
            self.target_config_str = format_config(
                build_engine_config(self.target_engine, path=self.target_path,
                                    settings=self.settings))
        except Exception:
            pass

    def _reload_opponent(self):
        self.queue.put(("status", "Reloading opponent engine…"))
        self._kill_engine(self.opponent_engine)
        self.opponent_engine = self._launch_engine(self.current_opponent_path,
                                                    is_adjudicator=False)
        try:
            name = get_engine_name(self.opponent_engine, self.opponent_name)
            if name:
                self.opponent_name = name
            self.opponent_config_str = format_config(
                build_engine_config(self.opponent_engine,
                                    path=self.current_opponent_path,
                                    settings=self.settings))
        except Exception:
            pass

    def _reload_adjudicator(self):
        self.queue.put(("status", "Reloading adjudicator…"))
        self._kill_engine(self.adjudicator_engine)
        self.adjudicator_engine = self._launch_engine(ADJUDICATOR_PATH,
                                                       is_adjudicator=True)

    def _safe_play(self, board, role):
        consecutive_target_fails = 0
        time_limit = self.settings.get("time", TIME_LIMIT)
        while True:
            if not self.running:
                raise TournamentAborted()
            engine = self.target_engine if role == "target" else self.opponent_engine
            try:
                result = engine.play(board, chess.engine.Limit(time=time_limit))
                if result is None or result.move is None:
                    raise ValueError("Engine returned no move")
                if result.move not in board.legal_moves:
                    raise ValueError(f"Engine returned illegal move: {result.move}")
                return result
            except Exception as e:
                self.queue.put(("status", f"{role.capitalize()} engine error: {e}"))
                if role == "opponent":
                    if self.opponent_reloaded:
                        raise OpponentDead()
                    try:
                        self._reload_opponent()
                        self.opponent_reloaded = True
                        self.queue.put(("status", "Opponent reloaded — retrying"))
                    except Exception as reload_err:
                        self.queue.put(("status", f"Opponent reload failed: {reload_err}"))
                        raise OpponentDead()
                else:
                    consecutive_target_fails += 1
                    if consecutive_target_fails > MAX_MOVE_RETRIES:
                        self.queue.put((
                            "error",
                            f"Target failed {MAX_MOVE_RETRIES} times consecutively — forfeiting game"))
                        raise TournamentAborted()
                    try:
                        self._reload_target()
                        self.queue.put(("status", "Target reloaded — retrying"))
                    except Exception as reload_err:
                        self.queue.put(("error", f"Could not reload target: {reload_err}"))
                        self.running = False
                        raise TournamentAborted()

    def _safe_analyse(self, board):
        if self.adjudicator_engine is None:
            return None
        for _ in range(3):
            if not self.running:
                return None
            try:
                return self.adjudicator_engine.analyse(board, chess.engine.Limit(time=0.2))
            except Exception as e:
                self.queue.put(("status", f"Adjudicator error: {e}"))
                try:
                    self._reload_adjudicator()
                except Exception as reload_err:
                    self.queue.put(("status", f"Adjudicator reload failed: {reload_err}"))
                    self.adjudicator_engine = None
                    return None
        return None

    def run(self):
        try:
            self.queue.put(("status", "Launching target engine…"))
            try:
                self.target_engine = self._launch_engine(self.target_path, is_adjudicator=False)
            except Exception as e:
                self.queue.put(("error", f"Could not launch target engine: {e}"))
                return
            self.target_name = get_engine_name(self.target_engine,
                                               os.path.basename(self.target_path))
            self.target_config_str = format_config(
                build_engine_config(self.target_engine, path=self.target_path,
                                    settings=self.settings))
            if is_maia_engine(self.target_engine, self.target_path):
                self.queue.put(("status", f"Target: {self.target_name} (Maia — NPS=1 applied)"))
            else:
                self.queue.put(("status", f"Target: {self.target_name} ({self.target_config_str})"))

            self.queue.put(("status", "Launching adjudicator…"))
            try:
                self.adjudicator_engine = self._launch_engine(ADJUDICATOR_PATH,
                                                              is_adjudicator=True)
            except Exception as e:
                self.queue.put(("error", f"Could not launch adjudicator: {e}"))
                self._kill_engine(self.target_engine)
                return

            for opp_idx, (opp_path, opp_rating) in enumerate(OPPONENTS):
                if not self.running:
                    break
                self.queue.put(("status", f"Launching opponent {opp_idx + 1}…"))
                self.current_opponent_path = opp_path
                self.opponent_reloaded = False
                try:
                    self.opponent_engine = self._launch_engine(opp_path, is_adjudicator=False)
                except Exception as launch_err:
                    self.queue.put(("status",
                        f"Opponent {opp_idx + 1} launch failed, skipping: {launch_err}"))
                    continue
                self.opponent_name = get_engine_name(self.opponent_engine,
                                                     os.path.basename(opp_path))
                self.opponent_rating = opp_rating
                self.current_opponent_index = opp_idx
                self.opponent_config_str = format_config(
                    build_engine_config(self.opponent_engine, path=opp_path,
                                        settings=self.settings))
                if is_maia_engine(self.opponent_engine, opp_path):
                    self.queue.put(("status",
                        f"Opponent: {self.opponent_name} (Maia — NPS=1 applied)"))

                per_game = []
                for game_idx in range(GAMES_PER_OPPONENT):
                    if not self.running:
                        break
                    target_is_white = (game_idx % 2 == 0)
                    try:
                        result = self.play_game(target_is_white)
                    except OpponentDead:
                        self.queue.put(("status",
                            f"Opponent '{self.opponent_name}' died twice — skipping remaining games"))
                        break
                    except TournamentAborted:
                        self.running = False
                        break
                    if result is None:
                        break
                    per_game.append(result)
                    self.games_played += 1
                    if result == "W":
                        self.wins += 1
                    elif result == "D":
                        self.draws += 1
                    else:
                        self.losses += 1
                w = per_game.count("W")
                d = per_game.count("D")
                l = per_game.count("L")
                if w + d + l > 0:
                    self.per_opponent_results.append(
                        (self.opponent_name, opp_rating, w, d, l))
                self._kill_engine(self.opponent_engine)
                self.opponent_engine = None

            self._kill_engine(self.target_engine)
            self._kill_engine(self.adjudicator_engine)
            self.target_engine = None
            self.adjudicator_engine = None

            if self.games_played == 0:
                self.queue.put(("done", None))
                return
            pool = [(r, w, d, l) for (_, r, w, d, l) in self.per_opponent_results]
            estimate = estimate_elo_vs_pool(pool)
            ci = confidence_interval_95(pool)
            self.queue.put(("done", (estimate, ci)))

        except Exception as e:
            self.queue.put(("error", str(e)))
            self._kill_engine(self.target_engine)
            self._kill_engine(self.opponent_engine)
            self._kill_engine(self.adjudicator_engine)

    def play_game(self, target_is_white):
        self.board.reset()
        self.current_move_number = 0
        self.last_move_san = ""
        self.last_move_uci = ""
        self.recent_moves = []
        self.current_fen_shared = self.board.fen()
        self.target_is_white = target_is_white
        self.last_game_was_checkmate = False
        max_moves = 300
        while (not self.board.is_game_over()) and self.current_move_number < max_moves:
            if not self.running:
                raise TournamentAborted()
            if (self.board.turn == chess.WHITE) == target_is_white:
                role = "target"
            else:
                role = "opponent"
            result = self._safe_play(self.board, role)
            try:
                san = self.board.san(result.move)
            except Exception:
                san = result.move.uci()
            self.board.push(result.move)
            self.current_move_number += 1
            self.last_move_san = san
            self.last_move_uci = result.move.uci()
            self.total_move_counter += 1
            self.recent_moves.append(san)
            if len(self.recent_moves) > 12:
                self.recent_moves = self.recent_moves[-12:]
            self.current_fen_shared = self.board.fen()
        outcome = self.board.outcome()
        try:
            self.last_game_was_checkmate = (
                outcome is not None
                and outcome.termination is not None
                and outcome.termination == chess.Termination.CHECKMATE)
        except Exception:
            self.last_game_was_checkmate = False
        if outcome is None:
            info = self._safe_analyse(self.board)
            white_wins = None
            if info is not None:
                try:
                    eval_score = info["score"].white().score(mate_score=10000)
                    if eval_score is None:
                        eval_score = 0
                    if eval_score > 200:
                        white_wins = True
                    elif eval_score < -200:
                        white_wins = False
                except Exception:
                    pass
            if white_wins is None:
                self.last_game_result = "Draw (adjudicated)"
                return "D"
            if white_wins == target_is_white:
                self.last_game_result = "Target wins (adjudicated)"
                return "W"
            self.last_game_result = "Opponent wins (adjudicated)"
            return "L"
        if outcome.winner is None:
            self.last_game_result = f"Draw ({outcome.termination.name})"
            return "D"
        if outcome.winner == chess.WHITE:
            if target_is_white:
                self.last_game_result = "Target wins (1-0)"
                return "W"
            self.last_game_result = "Opponent wins (1-0)"
            return "L"
        else:
            if target_is_white:
                self.last_game_result = "Opponent wins (0-1)"
                return "L"
            self.last_game_result = "Target wins (0-1)"
            return "W"

# ----------------------------------------------------------------------
# MAIN APPLICATION
# ----------------------------------------------------------------------
class EloifyApp:
    def __init__(self):
        pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
        pygame.init()
        _init_font_family()

        try:
            pygame.mixer.set_num_channels(24)
        except Exception:
            pass

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Eloify – Chess Engine Elo Tester")
        self.clock = pygame.time.Clock()

        self.drumroll_sound    = None
        self.celebration_sound = None
        self.move_sound        = None
        self.capture_sound     = None
        self.check_sound       = None
        self.checkmate_sound   = None
        self.win_sound         = None
        self.loss_sound        = None
        self.draw_sound        = None

        self.ch_check     = None
        self.ch_checkmate = None
        self.ch_win       = None
        self.ch_loss      = None
        self.ch_draw      = None

        if pygame.mixer.get_init():
            try:
                self.drumroll_sound    = _generate_drumroll()
                self.celebration_sound = _generate_celebration()
                self.move_sound        = _generate_move_sound()
                self.capture_sound     = _generate_capture_sound()
                self.check_sound       = _generate_check_sound()
                self.checkmate_sound   = _generate_checkmate_sound()
                self.win_sound         = _generate_win_sound()
                self.loss_sound        = _generate_loss_sound()
                self.draw_sound        = _generate_draw_sound()
                self.ch_check     = pygame.mixer.Channel(0)
                self.ch_checkmate = pygame.mixer.Channel(1)
                self.ch_win       = pygame.mixer.Channel(2)
                self.ch_loss      = pygame.mixer.Channel(3)
                self.ch_draw      = pygame.mixer.Channel(4)
            except Exception:
                pass

        self.state = "MENU"
        self.target_path = None
        self.worker = None
        self.progress_queue = queue.Queue()
        self.status_text = "Select a UCI engine to begin."
        self.estimated_elo = None
        self.estimate_kind = None
        self.confidence = None
        self.error_text = None
        self.start_time = None

        self.animation = None
        self.last_animated_fen = chess.STARTING_FEN
        self.last_animated_counter = 0
        self.last_move_from = None
        self.last_move_to = None

        self.done_start_time = None
        self.confetti = []
        self.confetti_spawned = False
        self._elo_surface_cache = None

        self.last_games_played = 0
        self.last_wins         = 0
        self.last_draws        = 0
        self.last_losses       = 0

        # ---- Detected system baseline ----
        self._actual_cpu = os.cpu_count() or 4
        self._actual_ram = _detect_total_ram_mb() or 2048

        # ---- Editable system settings ----
        self.cfg_cpu_cores = self._actual_cpu
        self.cfg_threads   = get_recommended_threads(cpu_cores=self._actual_cpu)
        self.cfg_hash      = get_recommended_hash_mb()
        self.cfg_time      = TIME_LIMIT

        self.settings_snapshot = None
        self.dragging_slider = None

        # ---- Browse dialog state ----
        self.browse_cwd = ""
        self.browse_entries = []
        self.browse_selected = -1
        self.browse_scroll = 0
        self.browse_error = ""
        self.browse_focus = "text"      # "text" or "list"
        self.browse_path_field = TextField("")
        self.browse_drag_active = False
        self._keys_down = set()
        self._last_browse_click_time = 0.0
        self._last_browse_click_idx = -1

        # ---- Main menu animation state ----
        self._menu_time = 0.0
        self._menu_bg_gradient = self._make_menu_bg_gradient()
        self._menu_title_glow = None
        self._menu_particles = []
        self._init_menu_particles()

        # Buttons (main menu — large, primary action on the right)
        self.browse_rect = pygame.Rect(60, 505, 420, 70)
        self.start_rect  = pygame.Rect(520, 505, 420, 70)
        self.edit_system_rect = pygame.Rect(400, 186, 60, 26)

        # Settings dialog buttons
        self.settings_reset_rect  = pygame.Rect(130, 600, 160, 44)
        self.settings_cancel_rect = pygame.Rect(630, 600, 110, 44)
        self.settings_save_rect   = pygame.Rect(760, 600, 110, 44)

        self.mouse_pos = (0, 0)

    # ------------------------------------------------------------------
    # MAIN MENU — decorative helpers
    # ------------------------------------------------------------------
    def _make_menu_bg_gradient(self):
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            t = y / max(1, WINDOW_HEIGHT - 1)
            r = int(BACKGROUND[0] * (0.85 + 0.35 * t))
            g = int(BACKGROUND[1] * (0.85 + 0.30 * t))
            b = int(BACKGROUND[2] * (0.85 + 0.20 * t))
            pygame.draw.line(surf, (r, g, b), (0, y), (WINDOW_WIDTH, y))
        return surf

    def _init_menu_particles(self):
        self._menu_particles = []
        glyphs = ["♟", "♞", "♝", "♜", "♛", "♚",
                  "♙", "♘", "♗", "♖", "♕", "♔"]
        for _ in range(16):
            self._menu_particles.append({
                'x': random.uniform(0, WINDOW_WIDTH),
                'y': random.uniform(0, WINDOW_HEIGHT),
                'vx': random.uniform(-10.0, 10.0),
                'vy': random.uniform(-18.0, -5.0),
                'size': random.randint(38, 84),
                'rot': random.uniform(0, 360),
                'rot_v': random.uniform(-10.0, 10.0),
                'alpha': random.randint(14, 30),
                'glyph': random.choice(glyphs),
            })

    def _update_menu_particles(self):
        dt = 1.0 / FPS
        self._menu_time += dt
        for p in self._menu_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['rot'] += p['rot_v'] * dt
            if p['y'] < -110:
                p['y'] = WINDOW_HEIGHT + 110
                p['x'] = random.uniform(0, WINDOW_WIDTH)
            if p['x'] < -110:
                p['x'] = WINDOW_WIDTH + 110
            elif p['x'] > WINDOW_WIDTH + 110:
                p['x'] = -110

    def _draw_menu_particles(self):
        for p in self._menu_particles:
            try:
                font = _get_piece_font(p['size'])
                surf = font.render(p['glyph'], True, ACCENT)
                surf.set_alpha(p['alpha'])
                rotated = pygame.transform.rotate(surf, p['rot'])
                self.screen.blit(rotated,
                                 rotated.get_rect(center=(int(p['x']), int(p['y']))))
            except Exception:
                continue

    def _get_menu_title_glow(self):
        if self._menu_title_glow is None:
            font = _get_font(_FONT_FAMILY, 68, True)
            glow = font.render("Eloify", True, ACCENT)
            w, h = glow.get_size()
            surf = pygame.Surface((w + 60, h + 60), pygame.SRCALPHA)
            for scale, alpha in ((1.35, 18), (1.18, 30), (1.06, 48)):
                gw, gh = int(w * scale), int(h * scale)
                try:
                    scaled = pygame.transform.smoothscale(glow, (gw, gh))
                except Exception:
                    continue
                scaled.set_alpha(alpha)
                surf.blit(scaled, ((w + 60 - gw) // 2, (h + 60 - gh) // 2))
            self._menu_title_glow = surf
        return self._menu_title_glow

    def _draw_menu_button(self, rect, label, enabled=True, primary=False):
        hovered = enabled and rect.collidepoint(self.mouse_pos)
        if not enabled:
            fill, border, text_color = (42, 46, 56), (60, 64, 76), (120, 125, 135)
        elif primary:
            pulse = 0.5 + 0.5 * math.sin(self._menu_time * 3.5)
            base = (78, 200, 148)
            bright = (105, 225, 172)
            mix = 0.55 + 0.45 * pulse
            fill = (
                int(base[0] + (bright[0] - base[0]) * mix),
                int(base[1] + (bright[1] - base[1]) * mix),
                int(base[2] + (bright[2] - base[2]) * mix),
            )
            if hovered:
                fill = (int(fill[0] * 1.08), int(fill[1] * 1.08), int(fill[2] * 1.08))
            border = (140, 245, 195)
            text_color = (12, 24, 18)
        elif hovered:
            fill, border, text_color = PANEL_HOVER, ACCENT, TEXT_COLOR
        else:
            fill, border, text_color = PANEL, BORDER, TEXT_COLOR
        pygame.draw.rect(self.screen, (12, 14, 18),
                         pygame.Rect(rect.x, rect.y + 3, rect.width, rect.height),
                         border_radius=12)
        if primary and enabled:
            glow_rect = rect.inflate(20, 20)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height),
                                       pygame.SRCALPHA)
            glow_alpha = 55 + int(35 * (0.5 + 0.5 * math.sin(self._menu_time * 3.5)))
            pygame.draw.rect(glow_surf, (*ACCENT, glow_alpha),
                             glow_surf.get_rect(), border_radius=20)
            self.screen.blit(glow_surf, glow_rect)
        pygame.draw.rect(self.screen, fill, rect, border_radius=12)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)
        surf = _render_text(label, 22, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_edit_button(self, rect):
        hovered = rect.collidepoint(self.mouse_pos)
        if hovered:
            fill = (48, 68, 58)
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = (44, 50, 60)
            border = BORDER
            text_color = DIM_TEXT
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
        surf = _render_text("Edit", 13, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_stat_panel(self, rect, title, rows, accent=ACCENT):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=12)
        pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=12)
        draw_text(self.screen, title, (rect.x + 20, rect.y + 16), 14, accent, bold=True)
        pygame.draw.line(self.screen, BORDER,
                         (rect.x + 20, rect.y + 40),
                         (rect.right - 20, rect.y + 40), 1)
        for i, (label, value, color) in enumerate(rows):
            ry = rect.y + 58 + i * 26
            draw_text(self.screen, label, (rect.x + 20, ry), 15, DIM_TEXT)
            vsurf = _render_text(str(value), 15, color or TEXT_COLOR, True)
            self.screen.blit(vsurf, (rect.right - 20 - vsurf.get_width(), ry))

    # ------------------------------------------------------------------
    # SETTINGS DIALOG
    # ------------------------------------------------------------------
    def _get_slider_rects(self):
        panel = pygame.Rect(100, 60, 800, 620)
        tracks = []
        for i in range(len(SLIDER_CONFIGS)):
            row_y = panel.y + 100 + i * 100
            track = pygame.Rect(panel.x + 30, row_y + 38, panel.w - 60, 6)
            tracks.append((track, row_y))
        return panel, tracks

    def _slider_params(self, key):
        for entry in SLIDER_CONFIGS:
            if entry[0] == key:
                return entry[2], entry[3], entry[4], entry[5]
        return (0, 1, 1, "int")

    def _get_setting_warnings(self):
        warnings = {}
        if self.cfg_cpu_cores > self._actual_cpu:
            warnings["cpu_cores"] = (
                f"Exceeds detected cores ({self._actual_cpu}) — may cause slowdown",
                ERROR_COLOR)
        elif self.cfg_cpu_cores < 4:
            warnings["cpu_cores"] = ("Engines may be weakened — fewer than 4 cores", GOLD)
        if self.cfg_threads > self.cfg_cpu_cores:
            warnings["threads"] = (
                f"More threads than CPU cores ({self.cfg_cpu_cores})", ERROR_COLOR)
        elif self.cfg_threads < 2:
            warnings["threads"] = ("Engines may be weakened — single-threaded", GOLD)
        safe_hash = max(64, self._actual_ram // 4)
        if self.cfg_hash > safe_hash:
            warnings["hash"] = (f"Exceeds safe memory limit ({safe_hash} MB)", ERROR_COLOR)
        elif self.cfg_hash < 64:
            warnings["hash"] = ("Engines may be weakened — very little hash", GOLD)
        if self.cfg_time > 0.5:
            warnings["time"] = ("Long per-move time — tournament will be slow", GOLD)
        return warnings

    def _format_slider_value(self, key):
        value = getattr(self, f"cfg_{key}")
        if key == "hash":
            return f"{int(value)} MB"
        if key == "time":
            return f"{value:.2f} s"
        return f"{int(value)}"

    def _update_slider_from_mouse(self, idx, mx):
        _, tracks = self._get_slider_rects()
        track, _ = tracks[idx]
        frac = max(0.0, min(1.0, (mx - track.x) / max(1, track.w)))
        key = SLIDER_CONFIGS[idx][0]
        vmin, vmax, step, kind = self._slider_params(key)
        raw = vmin + (vmax - vmin) * frac
        if kind == "int":
            value = int(round(raw / step) * step)
            value = max(int(vmin), min(int(vmax), value))
        else:
            value = round(raw / step) * step
            value = round(value, 2)
            value = max(vmin, min(vmax, value))
        setattr(self, f"cfg_{key}", value)

    def _draw_settings_button(self, rect, label, primary=False):
        hovered = rect.collidepoint(self.mouse_pos)
        if primary:
            fill = (105, 225, 172) if hovered else (78, 200, 148)
            border = (140, 245, 195)
            text_color = (12, 24, 18)
        elif hovered:
            fill = PANEL_HOVER
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = (44, 50, 60)
            border = BORDER
            text_color = TEXT_COLOR
        pygame.draw.rect(self.screen, (12, 14, 18),
                         pygame.Rect(rect.x, rect.y + 2, rect.w, rect.h),
                         border_radius=8)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=8)
        surf = _render_text(label, 16, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def open_settings(self):
        self.settings_snapshot = {
            "cpu_cores": self.cfg_cpu_cores,
            "threads":   self.cfg_threads,
            "hash":      self.cfg_hash,
            "time":      self.cfg_time,
        }
        self.dragging_slider = None
        self.state = "EDIT_SETTINGS"

    def settings_save(self):
        self.settings_snapshot = None
        self.dragging_slider = None
        self.state = "MENU"

    def settings_cancel(self):
        if self.settings_snapshot:
            self.cfg_cpu_cores = self.settings_snapshot["cpu_cores"]
            self.cfg_threads   = self.settings_snapshot["threads"]
            self.cfg_hash      = self.settings_snapshot["hash"]
            self.cfg_time      = self.settings_snapshot["time"]
        self.settings_snapshot = None
        self.dragging_slider = None
        self.state = "MENU"

    def settings_reset(self):
        self.cfg_cpu_cores = self._actual_cpu
        self.cfg_threads   = get_recommended_threads(cpu_cores=self._actual_cpu)
        self.cfg_hash      = get_recommended_hash_mb()
        self.cfg_time      = TIME_LIMIT

    def _handle_settings_click(self, pos):
        if self.settings_save_rect.collidepoint(pos):
            self.settings_save()
            return
        if self.settings_cancel_rect.collidepoint(pos):
            self.settings_cancel()
            return
        if self.settings_reset_rect.collidepoint(pos):
            self.settings_reset()
            return
        _, tracks = self._get_slider_rects()
        for i, (track, _) in enumerate(tracks):
            hit = pygame.Rect(track.x - 12, track.y - 20, track.w + 24, track.h + 40)
            if hit.collidepoint(pos):
                self.dragging_slider = i
                self._update_slider_from_mouse(i, pos[0])
                return

    # ------------------------------------------------------------------
    # BROWSE ENGINE DIALOG
    # ------------------------------------------------------------------
    def _open_browse_dialog(self):
        start_dir = None
        if self.target_path and os.path.exists(self.target_path):
            if os.path.isdir(self.target_path):
                start_dir = self.target_path
            else:
                start_dir = os.path.dirname(self.target_path)
        if not start_dir or not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")
            if not os.path.isdir(start_dir):
                start_dir = os.getcwd()

        self.browse_cwd = start_dir
        self.browse_path_field.set_text(start_dir)
        self.browse_selected = -1
        self.browse_scroll = 0
        self.browse_error = ""
        self.browse_focus = "text"
        self.browse_drag_active = False
        self._keys_down = set()
        self._last_browse_click_time = 0.0
        self._last_browse_click_idx = -1
        self._refresh_dir_listing()

        # Preselect current target file if it lives in this directory
        if self.target_path and os.path.isfile(self.target_path):
            target_norm = os.path.normpath(self.target_path)
            for i, (name, is_dir, full) in enumerate(self.browse_entries):
                if not is_dir and os.path.normpath(full) == target_norm:
                    self.browse_selected = i
                    self._browse_ensure_visible()
                    break

        # Enable OS-style key repeat while the dialog is open
        try:
            pygame.key.set_repeat(400, 35)
        except Exception:
            pass
        self.state = "BROWSE_ENGINE"

    def _close_browse_dialog(self, success=False):
        try:
            pygame.key.set_repeat()
        except Exception:
            pass
        self._keys_down = set()
        self.browse_drag_active = False
        self.state = "MENU"

    def _refresh_dir_listing(self):
        entries = []
        self.browse_error = ""
        try:
            items = list(os.scandir(self.browse_cwd))
            dirs = []
            files = []
            for e in items:
                try:
                    if e.is_dir():
                        dirs.append(e)
                    else:
                        files.append(e)
                except Exception:
                    continue
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())

            parent = os.path.dirname(self.browse_cwd)
            if parent and parent != self.browse_cwd:
                entries.append(("..", True, parent))
            for d in dirs:
                entries.append((d.name, True, d.path))
            for f in files:
                entries.append((f.name, False, f.path))
        except PermissionError:
            self.browse_error = f"Permission denied: {self.browse_cwd}"
        except Exception as e:
            self.browse_error = f"Error: {e}"
        self.browse_entries = entries
        if self.browse_selected >= len(self.browse_entries):
            self.browse_selected = -1

    def _browse_goto(self, path):
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            return
        self.browse_cwd = path
        self.browse_path_field.set_text(path)
        self.browse_selected = -1
        self.browse_scroll = 0
        self.browse_error = ""
        self._refresh_dir_listing()

    def _browse_ensure_visible(self):
        visible_rows = BROWSE_LIST.h // BROWSE_ROW_HEIGHT
        if self.browse_selected < self.browse_scroll:
            self.browse_scroll = self.browse_selected
        elif self.browse_selected >= self.browse_scroll + visible_rows:
            self.browse_scroll = self.browse_selected - visible_rows + 1

    def _browse_navigate_to_text(self):
        path = self.browse_path_field.text.strip()
        # Strip surrounding quotes (any nesting)
        changed = True
        while changed and len(path) >= 2:
            changed = False
            if path[0] in "\"'" and path[-1] == path[0]:
                path = path[1:-1].strip()
                changed = True
        if not path:
            self.browse_error = "No path specified"
            return
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        if os.path.isdir(path):
            self._browse_goto(path)
            return
        if os.path.isfile(path):
            self.target_path = path
            self.status_text = f"Selected: {os.path.basename(path)}"
            self._close_browse_dialog(success=True)
            return
        self.browse_error = f"Path not found: {path}"

    def _browse_activate_selected(self):
        if self.browse_selected < 0 or self.browse_selected >= len(self.browse_entries):
            return
        name, is_dir, full_path = self.browse_entries[self.browse_selected]
        if is_dir:
            self._browse_goto(full_path)
        else:
            self.target_path = full_path
            self.status_text = f"Selected: {os.path.basename(full_path)}"
            self._close_browse_dialog(success=True)

    def _handle_browse_open(self):
        # Prefer a selected file in the list
        if (self.browse_selected >= 0
                and self.browse_selected < len(self.browse_entries)):
            name, is_dir, full_path = self.browse_entries[self.browse_selected]
            if not is_dir:
                self.target_path = full_path
                self.status_text = f"Selected: {os.path.basename(full_path)}"
                self._close_browse_dialog(success=True)
                return
        # Otherwise use the text field
        self._browse_navigate_to_text()

    def _text_index_at(self, field_rect, field, mouse_x):
        font = _get_font(_FONT_FAMILY, 15)
        local_x = mouse_x - field_rect.x - BROWSE_FIELD_PADDING + field.scroll
        if local_x <= 0:
            return 0
        text = field.text
        for i in range(len(text) + 1):
            if font.size(text[:i])[0] > local_x:
                return max(0, i - 1)
        return len(text)

    def _handle_browse_click(self, pos):
        if BROWSE_CANCEL_RECT.collidepoint(pos):
            self._close_browse_dialog(success=False)
            return
        if BROWSE_OPEN_RECT.collidepoint(pos):
            self._handle_browse_open()
            return
        if BROWSE_UP_RECT.collidepoint(pos):
            parent = os.path.dirname(self.browse_cwd)
            if parent and parent != self.browse_cwd:
                self._browse_goto(parent)
            return
        if BROWSE_HOME_RECT.collidepoint(pos):
            home = os.path.expanduser("~")
            if os.path.isdir(home):
                self._browse_goto(home)
            return
        if BROWSE_REFRESH_RECT.collidepoint(pos):
            self._refresh_dir_listing()
            return
        if BROWSE_FIELD.collidepoint(pos):
            self.browse_focus = "text"
            field = self.browse_path_field
            idx = self._text_index_at(BROWSE_FIELD, field, pos[0])
            field.cursor = idx
            field.sel_start = idx
            field.sel_end = idx
            self.browse_drag_active = True
            return
        if BROWSE_LIST.collidepoint(pos):
            self.browse_focus = "list"
            list_x = pos[0] - BROWSE_LIST.x
            # Ignore scrollbar strip
            if list_x > BROWSE_LIST.w - 14:
                return
            row = (pos[1] - BROWSE_LIST.y - 4) // BROWSE_ROW_HEIGHT + self.browse_scroll
            if 0 <= row < len(self.browse_entries):
                self.browse_selected = row
                now = time.time()
                if (now - self._last_browse_click_time < 0.35
                        and self._last_browse_click_idx == row):
                    self._last_browse_click_time = 0.0
                    self._browse_activate_selected()
                else:
                    self._last_browse_click_time = now
                    self._last_browse_click_idx = row
            else:
                self.browse_selected = -1
            return

    def _handle_browse_key_down(self, event):
        key = event.key
        mods = event.mod
        ctrl = bool(mods & pygame.KMOD_CTRL)
        shift = bool(mods & pygame.KMOD_SHIFT)
        alt = bool(mods & pygame.KMOD_ALT)
        first = key not in self._keys_down
        self._keys_down.add(key)
        field = self.browse_path_field

        # Global shortcuts that work regardless of focus
        if ctrl and first:
            if key == pygame.K_a:
                field.select_all()
                return
            if key == pygame.K_c:
                if field.has_selection():
                    a, b = field.get_selection_range()
                    _set_clipboard_text(field.text[a:b])
                return
            if key == pygame.K_x:
                if field.has_selection():
                    a, b = field.get_selection_range()
                    _set_clipboard_text(field.text[a:b])
                    field.delete_selection()
                return
            if key == pygame.K_v:
                text = _get_clipboard_text()
                # Normalise: strip newlines, strip surrounding quotes
                text = text.replace("\r", "").replace("\n", "")
                text = text.strip()
                while len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
                    text = text[1:-1].strip()
                if text:
                    field.insert(text)
                return

        if first:
            if key == pygame.K_ESCAPE:
                self._close_browse_dialog(success=False)
                return
            if key == pygame.K_TAB:
                self.browse_focus = "text" if self.browse_focus == "list" else "list"
                if self.browse_focus == "list" and self.browse_selected < 0 and self.browse_entries:
                    self.browse_selected = 0
                    self._browse_ensure_visible()
                return

        if self.browse_focus == "text":
            if key == pygame.K_LEFT:
                field.move_cursor(-1, shift=shift)
                return
            if key == pygame.K_RIGHT:
                field.move_cursor(1, shift=shift)
                return
            if key == pygame.K_HOME:
                field.move_home(shift=shift)
                return
            if key == pygame.K_END:
                field.move_end(shift=shift)
                return
            if key == pygame.K_BACKSPACE:
                field.backspace()
                return
            if key == pygame.K_DELETE:
                field.delete()
                return
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if first:
                    self._browse_navigate_to_text()
                return
            if key == pygame.K_DOWN:
                if first and self.browse_entries:
                    self.browse_focus = "list"
                    self.browse_selected = max(0, self.browse_selected)
                    self._browse_ensure_visible()
                return
            # Character input
            if (event.unicode and event.unicode.isprintable()
                    and not ctrl and not alt):
                field.insert(event.unicode)
            return

        # list focus
        if key == pygame.K_UP:
            if self.browse_selected > 0:
                self.browse_selected -= 1
                self._browse_ensure_visible()
            return
        if key == pygame.K_DOWN:
            if self.browse_selected < len(self.browse_entries) - 1:
                self.browse_selected += 1
                self._browse_ensure_visible()
            return
        if key == pygame.K_HOME:
            self.browse_selected = 0
            self._browse_ensure_visible()
            return
        if key == pygame.K_END:
            if self.browse_entries:
                self.browse_selected = len(self.browse_entries) - 1
                self._browse_ensure_visible()
            return
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if first:
                self._browse_activate_selected()
            return

    def _draw_browse_tool_button(self, rect, label, enabled=True):
        hovered = enabled and rect.collidepoint(self.mouse_pos)
        if not enabled:
            fill = (30, 34, 42)
            border = (40, 44, 52)
            text_color = (90, 95, 105)
        elif hovered:
            fill = PANEL_HOVER
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = (44, 50, 60)
            border = BORDER
            text_color = TEXT_COLOR
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
        surf = _render_text(label, 14, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_browse_button(self, rect, label, primary=False):
        hovered = rect.collidepoint(self.mouse_pos)
        if primary:
            fill = (105, 225, 172) if hovered else (78, 200, 148)
            border = (140, 245, 195)
            text_color = (12, 24, 18)
        elif hovered:
            fill = PANEL_HOVER
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = (44, 50, 60)
            border = BORDER
            text_color = TEXT_COLOR
        pygame.draw.rect(self.screen, (12, 14, 18),
                         pygame.Rect(rect.x, rect.y + 2, rect.w, rect.h),
                         border_radius=8)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=8)
        surf = _render_text(label, 16, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_text_field(self, field_rect, field, focused=True):
        pygame.draw.rect(self.screen, FIELD_BG, field_rect, border_radius=6)
        border_color = ACCENT if focused else FIELD_BORDER
        pygame.draw.rect(self.screen, border_color, field_rect,
                         width=2, border_radius=6)

        font = _get_font(_FONT_FAMILY, 15)
        padding = BROWSE_FIELD_PADDING
        text = field.text
        visible_w = field_rect.w - padding * 2
        text_w = font.size(text)[0] if text else 0

        # Recompute horizontal scroll so cursor stays visible
        if text_w <= visible_w:
            field.scroll = 0
        else:
            cursor_x = font.size(text[:field.cursor])[0] if text else 0
            if cursor_x > field.scroll + visible_w:
                field.scroll = cursor_x - visible_w
            elif cursor_x < field.scroll:
                field.scroll = cursor_x
            field.scroll = max(0, min(field.scroll, text_w - visible_w))
        scroll = field.scroll

        old_clip = self.screen.get_clip()
        clip_rect = pygame.Rect(field_rect.x + padding, field_rect.y + 4,
                                visible_w, field_rect.h - 8)
        self.screen.set_clip(clip_rect)

        # Selection highlight
        if field.has_selection():
            a, b = field.get_selection_range()
            x1 = field_rect.x + padding + font.size(text[:a])[0] - scroll
            x2 = field_rect.x + padding + font.size(text[:b])[0] - scroll
            pygame.draw.rect(self.screen, SELECTION_BG,
                             pygame.Rect(int(x1), field_rect.y + 6,
                                         int(x2 - x1), field_rect.h - 12))

        if text:
            text_surf = font.render(text, True, TEXT_COLOR)
            self.screen.blit(
                text_surf,
                (field_rect.x + padding - scroll,
                 field_rect.y + (field_rect.h - text_surf.get_height()) // 2))
        else:
            color = (90, 95, 105) if focused else (100, 105, 115)
            ph = _render_text("Paste or type a path…", 15, color, False)
            self.screen.blit(
                ph,
                (field_rect.x + padding,
                 field_rect.y + (field_rect.h - ph.get_height()) // 2))

        # Cursor (only when focused, blinks ~2Hz)
        if focused and int(time.time() * 2) % 2 == 0:
            cursor_x = (field_rect.x + padding
                        + (font.size(text[:field.cursor])[0] if text else 0)
                        - scroll)
            pygame.draw.line(self.screen, TEXT_COLOR,
                             (int(cursor_x), field_rect.y + 7),
                             (int(cursor_x), field_rect.y + field_rect.h - 7), 2)

        self.screen.set_clip(old_clip)

    def _draw_browse_list(self):
        rect = BROWSE_LIST
        row_h = BROWSE_ROW_HEIGHT
        visible_rows = rect.h // row_h
        max_scroll = max(0, len(self.browse_entries) - visible_rows)
        self.browse_scroll = max(0, min(self.browse_scroll, max_scroll))

        font = _get_font(_FONT_FAMILY, 14)

        for i in range(visible_rows):
            idx = self.browse_scroll + i
            if idx >= len(self.browse_entries):
                break
            name, is_dir, full_path = self.browse_entries[idx]
            row_y = rect.y + 4 + i * row_h
            row_rect = pygame.Rect(rect.x + 4, row_y, rect.w - 20, row_h - 2)

            hovered = row_rect.collidepoint(self.mouse_pos)
            selected = (idx == self.browse_selected)

            if selected:
                pygame.draw.rect(self.screen, LIST_ROW_SEL, row_rect, border_radius=4)
            elif hovered:
                pygame.draw.rect(self.screen, LIST_ROW_HOVER, row_rect, border_radius=4)

            if name == "..":
                display = "↑  .."
                color = DIM_TEXT
            elif is_dir:
                display = name + "/"
                color = ACCENT
            else:
                display = name
                color = TEXT_COLOR

            max_w = row_rect.w - 16
            if font.size(display)[0] > max_w:
                while len(display) > 4 and font.size(display + "…")[0] > max_w:
                    display = display[:-1]
                display += "…"

            surf = font.render(display, True, color)
            self.screen.blit(
                surf,
                (row_rect.x + 8, row_y + (row_h - surf.get_height()) // 2 - 1))

        # Scrollbar
        if max_scroll > 0:
            bar_x = rect.right - 10
            bar_y = rect.y + 4
            bar_h = rect.h - 8
            thumb_h = max(24, int(bar_h * visible_rows / len(self.browse_entries)))
            thumb_y = bar_y + int((bar_h - thumb_h) * self.browse_scroll / max_scroll)
            pygame.draw.rect(self.screen, (60, 66, 80),
                             pygame.Rect(bar_x, bar_y, 4, bar_h), border_radius=2)
            pygame.draw.rect(self.screen, ACCENT,
                             pygame.Rect(bar_x, thumb_y, 4, thumb_h),
                             border_radius=2)

    def draw_browse_overlay(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 205))
        self.screen.blit(dim, (0, 0))

        panel = BROWSE_PANEL
        pygame.draw.rect(self.screen, (10, 12, 16),
                         pygame.Rect(panel.x, panel.y + 4, panel.w, panel.h),
                         border_radius=16)
        draw_rounded_panel(self.screen, panel, fill=PANEL, border=BORDER, radius=16)

        # Header
        draw_text(self.screen, "Browse for UCI Engine",
                  (panel.x + 30, panel.y + 20), 26, ACCENT, bold=True)
        draw_text(self.screen,
                  "Navigate folders or paste a path · Ctrl+V to paste · Ctrl+A to select all",
                  (panel.x + 30, panel.y + 54), 14, DIM_TEXT)
        pygame.draw.line(self.screen, BORDER,
                         (panel.x + 30, panel.y + 82),
                         (panel.right - 30, panel.y + 82), 1)

        # Text field
        self._draw_text_field(BROWSE_FIELD, self.browse_path_field,
                              focused=(self.browse_focus == "text"))

        # Toolbar
        parent_ok = os.path.dirname(self.browse_cwd) != self.browse_cwd
        self._draw_browse_tool_button(BROWSE_UP_RECT, "↑ Up", enabled=parent_ok)
        self._draw_browse_tool_button(BROWSE_HOME_RECT, "Home")
        self._draw_browse_tool_button(BROWSE_REFRESH_RECT, "Refresh")

        # List
        pygame.draw.rect(self.screen, LIST_BG, BROWSE_LIST, border_radius=8)
        pygame.draw.rect(self.screen, BORDER, BROWSE_LIST, width=1, border_radius=8)
        self._draw_browse_list()

        # Info / error
        if self.browse_error:
            info_text = self.browse_error
            info_color = ERROR_COLOR
        else:
            n_dirs = sum(1 for e in self.browse_entries if e[1] and e[0] != "..")
            n_files = sum(1 for e in self.browse_entries if not e[1])
            info_text = f"{n_dirs} folders  ·  {n_files} files"
            info_color = DIM_TEXT
        draw_text(self.screen, info_text,
                  (panel.x + 30, BROWSE_INFO_Y), 13, info_color)

        # Buttons
        self._draw_browse_button(BROWSE_CANCEL_RECT, "Cancel", primary=False)
        self._draw_browse_button(BROWSE_OPEN_RECT, "Open", primary=True)

    # ------------------------------------------------------------------
    def run(self):
        while True:
            self.mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.shutdown()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.mouse_pos = event.pos
                    self.handle_click(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.mouse_pos = event.pos
                    self.handle_mouse_up(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                    self.handle_mouse_motion(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    self.handle_mouse_wheel(event)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down(event)
                elif event.type == pygame.KEYUP:
                    self.handle_key_up(event)
            self.process_queue()
            self.draw()
            self.clock.tick(FPS)

    def handle_key_down(self, event):
        if self.state == "BROWSE_ENGINE":
            self._handle_browse_key_down(event)

    def handle_key_up(self, event):
        if self.state == "BROWSE_ENGINE":
            self._keys_down.discard(event.key)

    def handle_mouse_wheel(self, event):
        if self.state == "BROWSE_ENGINE":
            if BROWSE_LIST.collidepoint(self.mouse_pos):
                self.browse_scroll -= event.y
                visible = BROWSE_LIST.h // BROWSE_ROW_HEIGHT
                max_scroll = max(0, len(self.browse_entries) - visible)
                self.browse_scroll = max(0, min(self.browse_scroll, max_scroll))

    def handle_click(self, pos):
        if self.state == "MENU":
            if self.browse_rect.collidepoint(pos):
                self._open_browse_dialog()
            elif self.start_rect.collidepoint(pos) and self.target_path:
                self.start_tournament()
            elif self.edit_system_rect.collidepoint(pos):
                self.open_settings()
        elif self.state == "EDIT_SETTINGS":
            self._handle_settings_click(pos)
        elif self.state == "BROWSE_ENGINE":
            self._handle_browse_click(pos)
        elif self.state == "DONE":
            if self.done_start_time is not None:
                elapsed = time.time() - self.done_start_time
                if elapsed < REVEAL_DURATION + ELO_POP_DURATION:
                    return
            self.reset()

    def handle_mouse_up(self, pos):
        if self.state == "EDIT_SETTINGS":
            self.dragging_slider = None
        elif self.state == "BROWSE_ENGINE":
            if self.browse_drag_active:
                self.browse_drag_active = False
                field = self.browse_path_field
                if field.sel_start == field.sel_end:
                    field.clear_selection()

    def handle_mouse_motion(self, pos):
        if self.state == "EDIT_SETTINGS" and self.dragging_slider is not None:
            self._update_slider_from_mouse(self.dragging_slider, pos[0])
        elif self.state == "BROWSE_ENGINE" and self.browse_drag_active:
            field = self.browse_path_field
            idx = self._text_index_at(BROWSE_FIELD, field, pos[0])
            field.cursor = idx
            field.sel_end = idx
            if field.sel_start is None:
                field.sel_start = idx

    def start_tournament(self):
        self.state = "RUNNING"
        self.error_text = None
        self.status_text = "Starting tournament…"
        self.start_time = time.time()
        self.progress_queue = queue.Queue()
        self.animation = None
        self.last_animated_fen = chess.STARTING_FEN
        self.last_animated_counter = 0
        self.last_move_from = None
        self.last_move_to = None
        self.done_start_time = None
        self.confetti = []
        self.confetti_spawned = False
        self._elo_surface_cache = None
        self.last_games_played = 0
        self.last_wins         = 0
        self.last_draws        = 0
        self.last_losses       = 0
        settings = {
            "threads": self.cfg_threads,
            "hash":    self.cfg_hash,
            "time":    self.cfg_time,
        }
        self.worker = TournamentWorker(self.target_path, self.progress_queue, settings)
        self.worker.start()

    def process_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg[0] == "status":
                    self.status_text = msg[1]
                elif msg[0] == "done":
                    self.state = "DONE"
                    self.done_start_time = time.time()
                    self.confetti = []
                    self.confetti_spawned = False
                    estimate = msg[1]
                    if estimate is None:
                        self.estimated_elo = None
                        self.estimate_kind = None
                        self.confidence = None
                    else:
                        self.estimate_kind, self.estimated_elo = estimate[0]
                        self.confidence = estimate[1]
                    if self.drumroll_sound and self.estimated_elo is not None and not self.error_text:
                        try:
                            self.drumroll_sound.play()
                        except Exception:
                            pass
                elif msg[0] == "error":
                    self.state = "DONE"
                    self.estimated_elo = None
                    self.error_text = msg[1]
                    self.done_start_time = time.time()
        except queue.Empty:
            pass

    def _make_animation(self, prev_fen, fen, uci_move):
        if not uci_move or len(uci_move) < 4:
            return None
        try:
            from_sq = chess.parse_square(uci_move[:2])
            to_sq = chess.parse_square(uci_move[2:4])
        except Exception:
            return None
        board = _get_board(fen)
        piece = board.piece_at(to_sq)
        rook_from = rook_to = None
        if piece is not None and piece.piece_type == chess.KING:
            if abs(chess.square_file(from_sq) - chess.square_file(to_sq)) == 2:
                rank = chess.square_rank(from_sq)
                if chess.square_file(to_sq) == 6:
                    rook_from, rook_to = chess.square(7, rank), chess.square(5, rank)
                else:
                    rook_from, rook_to = chess.square(0, rank), chess.square(3, rank)
        captured_sq = None
        captured_sym = None
        if prev_fen is not None:
            try:
                pb = chess.Board(prev_fen)
                cp = pb.piece_at(to_sq)
                if cp:
                    captured_sq = to_sq
                    captured_sym = cp.symbol()
                else:
                    mover = pb.piece_at(from_sq)
                    if mover and mover.piece_type == chess.PAWN:
                        if chess.square_file(from_sq) != chess.square_file(to_sq):
                            cap_sq = (to_sq - 8) if mover.color == chess.WHITE else (to_sq + 8)
                            cap_piece = pb.piece_at(cap_sq)
                            if cap_piece and cap_piece.piece_type == chess.PAWN:
                                captured_sq = cap_sq
                                captured_sym = cap_piece.symbol()
            except Exception:
                pass
        return MoveAnimation(from_sq, to_sq, rook_from, rook_to,
                             captured_sq, captured_sym)

    def _update_animation(self):
        w = self.worker
        if w is None:
            return
        if w.current_fen_shared != self.last_animated_fen:
            prev_fen = self.last_animated_fen
            self.last_animated_fen = w.current_fen_shared
            if w.total_move_counter != self.last_animated_counter:
                self.last_animated_counter = w.total_move_counter
                if w.last_move_uci and len(w.last_move_uci) >= 4:
                    try:
                        self.last_move_from = chess.parse_square(w.last_move_uci[:2])
                        self.last_move_to   = chess.parse_square(w.last_move_uci[2:4])
                    except Exception:
                        self.last_move_from = None
                        self.last_move_to = None
                self.animation = self._make_animation(prev_fen,
                                                      w.current_fen_shared,
                                                      w.last_move_uci)
                if self.animation is not None and w.last_move_san:
                    is_capture = "x" in w.last_move_san
                    snd = self.capture_sound if (is_capture and self.capture_sound) else self.move_sound
                    if snd is not None:
                        try:
                            snd.play()
                        except Exception:
                            pass
                try:
                    b = _get_board(w.current_fen_shared)
                    if b.is_checkmate():
                        pass
                    elif b.is_check() and self.check_sound and self.ch_check is not None:
                        try:
                            self.ch_check.play(self.check_sound)
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                self.animation = None
                self.last_move_from = None
                self.last_move_to = None
        if self.animation is not None and self.animation.done():
            self.animation = None

    def _update_game_sounds(self):
        w = self.worker
        if w is None:
            return
        if w.games_played > self.last_games_played:
            if getattr(w, "last_game_was_checkmate", False):
                if self.checkmate_sound and self.ch_checkmate is not None:
                    try:
                        self.ch_checkmate.play(self.checkmate_sound)
                    except Exception:
                        pass
            else:
                new_wins   = w.wins   - self.last_wins
                new_draws  = w.draws  - self.last_draws
                new_losses = w.losses - self.last_losses
                if new_wins > 0 and self.win_sound and self.ch_win is not None:
                    try:
                        self.ch_win.play(self.win_sound)
                    except Exception:
                        pass
                elif new_losses > 0 and self.loss_sound and self.ch_loss is not None:
                    try:
                        self.ch_loss.play(self.loss_sound)
                    except Exception:
                        pass
                elif new_draws > 0 and self.draw_sound and self.ch_draw is not None:
                    try:
                        self.ch_draw.play(self.draw_sound)
                    except Exception:
                        pass
            self.last_games_played = w.games_played
            self.last_wins         = w.wins
            self.last_draws        = w.draws
            self.last_losses       = w.losses

    def _spawn_confetti(self):
        colors = [
            (255, 100, 100), (255, 200, 50), (100, 255, 100),
            (100, 200, 255), (255, 100, 255), (255, 255, 100),
            (200, 100, 255), (100, 255, 200), GOLD,
        ]
        self.confetti = []
        for _ in range(260):
            x = random.uniform(0, WINDOW_WIDTH)
            y = random.uniform(-300, 0)
            vx = random.uniform(-140, 140)
            vy = random.uniform(40, 200)
            self.confetti.append({
                'x': x, 'y': y, 'vx': vx, 'vy': vy,
                'color': random.choice(colors),
                'size': random.randint(6, 14),
                'rot': random.uniform(0, 360),
                'rot_v': random.uniform(-400, 400),
            })

    def _update_and_draw_confetti(self):
        if not self.confetti:
            return
        dt = 1.0 / FPS
        alive = []
        for p in self.confetti:
            p['vy'] += 400 * dt
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['rot'] += p['rot_v'] * dt
            p['x'] += math.sin(p['y'] * 0.05) * 0.6
            if p['y'] < WINDOW_HEIGHT + 60:
                alive.append(p)
                w = p['size']
                h = max(3, p['size'] // 2)
                cos_r, sin_r = math.cos(p['rot']), math.sin(p['rot'])
                corners = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
                rotated = [
                    (p['x'] + cx * cos_r - cy * sin_r,
                     p['y'] + cx * sin_r + cy * cos_r)
                    for cx, cy in corners
                ]
                pygame.draw.polygon(self.screen, p['color'], rotated)
        self.confetti = alive

    def _draw_mystery_reveal(self, elapsed):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 235))
        self.screen.blit(overlay, (0, 0))
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        for i in range(18):
            phase = ((elapsed * 0.5) + i * 0.4) % 1.0
            x = 80 + (i * 137) % (WINDOW_WIDTH - 160)
            y = WINDOW_HEIGHT - phase * (WINDOW_HEIGHT + 50)
            alpha = int(200 * (1 - phase))
            if alpha > 0:
                qfont = _get_font(_FONT_FAMILY, 22, True)
                qsurf = qfont.render("?", True, (255, 220, 100))
                qsurf.set_alpha(alpha)
                self.screen.blit(qsurf, (int(x), int(y)))
        spinner_angle = elapsed * 5
        radius = 150
        for i in range(12):
            a = i * math.pi / 6
            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            diff = abs(((a - spinner_angle) % (2 * math.pi)) - math.pi)
            brightness = max(0.0, 1.0 - diff / math.pi)
            c = int(255 * brightness)
            pygame.draw.circle(self.screen, (c, int(c * 0.8), 0), (int(x), int(y)), 5)
        pulse = 0.5 + 0.5 * math.sin(elapsed * 7)
        size = int(40 + pulse * 8)
        dots = "." * ((int(elapsed * 3) % 4))
        msg = f"CALCULATING ELO{dots}"
        font = _get_font(_FONT_FAMILY, size, True)
        surf = font.render(msg, True, (255, 220, 100))
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
        glow_alpha = int(40 + 60 * pulse)
        halo_size = int(220 + 40 * pulse)
        halo = pygame.Surface((halo_size * 2, halo_size * 2), pygame.SRCALPHA)
        for r in range(halo_size, 0, -12):
            a = int(glow_alpha * (1 - r / halo_size))
            pygame.draw.circle(halo, (255, 200, 50, a), (halo_size, halo_size), r)
        self.screen.blit(halo, (cx - halo_size, cy - halo_size))

    def _draw_elo_pop(self, cy, pop_elapsed):
        elo_str = f"{self.estimated_elo:.0f}"
        if self.estimate_kind == "lower_bound":
            elo_str = f"≥ {elo_str}"
        elif self.estimate_kind == "upper_bound":
            elo_str = f"≤ {elo_str}"
        cx = WINDOW_WIDTH // 2
        cache_key = (elo_str, self.estimate_kind)
        if self._elo_surface_cache is None or self._elo_surface_cache[0] != cache_key:
            base_font = _get_font(_FONT_FAMILY, 64, True)
            base_surf = base_font.render(elo_str, True, GOLD)
            glow_base = base_font.render(elo_str, True, (255, 180, 60))
            self._elo_surface_cache = (cache_key, base_surf, glow_base)
        _, base_surf, glow_base = self._elo_surface_cache
        bw, bh = base_surf.get_size()
        pop_t = min(1.0, pop_elapsed / ELO_POP_DURATION) if pop_elapsed < ELO_POP_DURATION else 1.0
        scale = ease_out_back(pop_t, 3.0)
        if scale > 0.05:
            halo_radius = int((bw // 2 + 90) * scale)
            if halo_radius > 4:
                halo = pygame.Surface((halo_radius * 2, halo_radius * 2), pygame.SRCALPHA)
                for r in range(halo_radius, 0, -10):
                    a = int(70 * (1 - r / halo_radius))
                    pygame.draw.circle(halo, (255, 190, 40, a),
                                       (halo_radius, halo_radius), r)
                self.screen.blit(halo, (cx - halo_radius, cy - halo_radius))
        for i in range(4, 0, -1):
            gs = scale * (1.0 + i * 0.09)
            gw, gh = max(1, int(bw * gs)), max(1, int(bh * gs))
            if gw > 4 and gh > 4:
                try:
                    glow = pygame.transform.scale(glow_base, (gw, gh))
                    glow.set_alpha(int(45 / i))
                    self.screen.blit(glow, glow.get_rect(center=(cx, cy)))
                except Exception:
                    pass
        tw, th = max(1, int(bw * scale)), max(1, int(bh * scale))
        if tw > 4 and th > 4:
            try:
                scaled = pygame.transform.smoothscale(base_surf, (tw, th))
                self.screen.blit(scaled, scaled.get_rect(center=(cx, cy)))
            except Exception:
                pass
        label_alpha = min(255, int(255 * max(0.0, (pop_elapsed - 0.2) / 0.4)))
        if label_alpha > 0:
            lf = _get_font(_FONT_FAMILY, 20, True)
            label = lf.render("ESTIMATED ELO", True, DIM_TEXT)
            label.set_alpha(label_alpha)
            self.screen.blit(label, label.get_rect(center=(cx, cy - 80)))
            if self.confidence is not None and self.estimate_kind == "ok":
                cf = _get_font(_FONT_FAMILY, 18, False)
                ci = cf.render(f"± {self.confidence:.0f}  (95% confidence)",
                               True, DIM_TEXT)
                ci.set_alpha(label_alpha)
                self.screen.blit(ci, ci.get_rect(center=(cx, cy + 70)))

    def draw(self):
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "EDIT_SETTINGS":
            real_mouse = self.mouse_pos
            self.mouse_pos = (-9999, -9999)
            self.draw_menu()
            self.mouse_pos = real_mouse
            self.draw_settings_overlay()
        elif self.state == "BROWSE_ENGINE":
            real_mouse = self.mouse_pos
            self.mouse_pos = (-9999, -9999)
            self.draw_menu()
            self.mouse_pos = real_mouse
            self.draw_browse_overlay()
        else:
            self.screen.fill(BACKGROUND)
            self._update_game_sounds()
            if self.state == "RUNNING":
                self.draw_running()
            elif self.state == "DONE":
                self.draw_done()
        pygame.display.flip()

    def draw_settings_overlay(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 205))
        self.screen.blit(dim, (0, 0))
        panel, tracks = self._get_slider_rects()
        pygame.draw.rect(self.screen, (10, 12, 16),
                         pygame.Rect(panel.x, panel.y + 4, panel.w, panel.h),
                         border_radius=16)
        draw_rounded_panel(self.screen, panel, fill=PANEL, border=BORDER, radius=16)
        draw_text(self.screen, "Settings", (panel.x + 30, panel.y + 22),
                  28, ACCENT, bold=True)
        draw_text(self.screen, "Adjust tournament parameters",
                  (panel.x + 30, panel.y + 60), 15, DIM_TEXT)
        pygame.draw.line(self.screen, BORDER,
                         (panel.x + 30, panel.y + 90),
                         (panel.right - 30, panel.y + 90), 1)
        warnings = self._get_setting_warnings()
        for i, (track, row_y) in enumerate(tracks):
            key, label, _, _, _, _ = SLIDER_CONFIGS[i]
            value = getattr(self, f"cfg_{key}")
            vmin, vmax, _, _ = self._slider_params(key)
            draw_text(self.screen, label, (panel.x + 30, row_y),
                      16, TEXT_COLOR, bold=True)
            val_str = self._format_slider_value(key)
            vsurf = _render_text(val_str, 18, GOLD, True)
            self.screen.blit(vsurf, (panel.right - 30 - vsurf.get_width(), row_y - 2))
            frac = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
            fill_color = warnings[key][1] if key in warnings else ACCENT
            pygame.draw.rect(self.screen, (45, 50, 62), track, border_radius=3)
            fill_w = int(track.w * frac)
            if fill_w > 0:
                pygame.draw.rect(self.screen, fill_color,
                                 pygame.Rect(track.x, track.y, fill_w, track.h),
                                 border_radius=3)
            knob_x = track.x + fill_w
            knob_y = track.centery
            pygame.draw.circle(self.screen, (12, 14, 18), (knob_x, knob_y), 11)
            pygame.draw.circle(self.screen, TEXT_COLOR, (knob_x, knob_y), 9)
            pygame.draw.circle(self.screen, fill_color, (knob_x, knob_y), 9, width=2)
            if key in warnings:
                wtext, wcolor = warnings[key]
                pygame.draw.circle(self.screen, wcolor,
                                   (panel.x + 36, row_y + 60), 4)
                draw_text(self.screen, wtext, (panel.x + 48, row_y + 52),
                          13, wcolor)
        self._draw_settings_button(self.settings_reset_rect,
                                   "Reset Defaults", primary=False)
        self._draw_settings_button(self.settings_cancel_rect,
                                   "Cancel", primary=False)
        self._draw_settings_button(self.settings_save_rect,
                                   "Save", primary=True)

    def draw_menu(self):
        self.screen.blit(self._menu_bg_gradient, (0, 0))
        self._update_menu_particles()
        self._draw_menu_particles()
        knight_font = _get_piece_font(72)
        try:
            knight = knight_font.render("♞", True, ACCENT)
        except Exception:
            knight = None
        title_font = _get_font(_FONT_FAMILY, 68, True)
        title_surf = title_font.render("Eloify", True, ACCENT)
        th = title_surf.get_height()
        kx = 60
        if knight is not None:
            ky = 34 + (th - knight.get_height()) // 2
            self.screen.blit(knight, (kx, ky))
            tx = kx + knight.get_width() + 14
        else:
            tx = kx
        glow = self._get_menu_title_glow()
        pulse_alpha = 90 + int(70 * (0.5 + 0.5 * math.sin(self._menu_time * 2.0)))
        glow_copy = glow.copy()
        glow_copy.set_alpha(pulse_alpha)
        self.screen.blit(
            glow_copy,
            (tx - 30, 30 + (th - glow_copy.get_height()) // 2 + 4))
        self.screen.blit(title_surf, (tx, 34))
        draw_text(self.screen, "v1.0", (WINDOW_WIDTH - 90, 52), 16, DIM_TEXT, bold=True)
        draw_text(self.screen, "Chess Engine Elo Tester",
                  (60, 128), 20, DIM_TEXT)
        pygame.draw.line(self.screen, BORDER,
                         (60, 158), (WINDOW_WIDTH - 60, 158), 1)

        left_rows = [
            ("CPU cores",        str(self.cfg_cpu_cores),               TEXT_COLOR),
            ("Threads / engine", str(self.cfg_threads),                 TEXT_COLOR),
            ("Hash / engine",    f"{int(self.cfg_hash)} MB",            TEXT_COLOR),
            ("Time / move",      f"{self.cfg_time:.2f} s",              TEXT_COLOR),
        ]
        self._draw_stat_panel(pygame.Rect(60, 176, 420, 184),
                              "SYSTEM", left_rows, accent=ACCENT)
        self._draw_edit_button(self.edit_system_rect)

        right_rows = [
            ("Opponents", str(len(OPPONENTS)), TEXT_COLOR),
            ("Games / opponent", str(GAMES_PER_OPPONENT), TEXT_COLOR),
            ("Total games", str(len(OPPONENTS) * GAMES_PER_OPPONENT), GOLD),
        ]
        if OPPONENTS:
            lo = min(r for _, r in OPPONENTS)
            hi = max(r for _, r in OPPONENTS)
            right_rows.append(("Rating range", f"{lo} – {hi}", TEXT_COLOR))
        self._draw_stat_panel(pygame.Rect(520, 176, 420, 184),
                              "ENGINE POOL", right_rows, accent=GOLD)

        status_rect = pygame.Rect(60, 380, 880, 96)
        pygame.draw.rect(self.screen, PANEL, status_rect, border_radius=12)
        pygame.draw.rect(self.screen, BORDER, status_rect, width=1, border_radius=12)
        draw_text(self.screen, "STATUS",
                  (status_rect.x + 20, status_rect.y + 14), 13, ACCENT, bold=True)
        draw_text(self.screen, self.status_text,
                  (status_rect.x + 20, status_rect.y + 40), 18, TEXT_COLOR)
        draw_text(self.screen, "Adjudicator: " + os.path.basename(ADJUDICATOR_PATH),
                  (status_rect.x + 20, status_rect.y + 68), 13, DIM_TEXT)

        if self.target_path:
            fname = os.path.basename(self.target_path)
            disp = fname if len(fname) <= 38 else fname[:35] + "…"
            chip_font_w = _render_text(disp, 15, WIN_COLOR, True).get_width()
            chip_w = min(560, chip_font_w + 60)
            chip_x = status_rect.right - chip_w - 20
            chip_rect = pygame.Rect(chip_x, status_rect.y + 26, chip_w, 46)
            pygame.draw.rect(self.screen, (32, 62, 48), chip_rect, border_radius=8)
            pygame.draw.rect(self.screen, (75, 160, 115), chip_rect,
                             width=1, border_radius=8)
            draw_text(self.screen, "✓",
                      (chip_rect.x + 14, chip_rect.y + 12), 18, WIN_COLOR, bold=True)
            draw_text(self.screen, disp,
                      (chip_rect.x + 42, chip_rect.y + 14), 15, WIN_COLOR, bold=True)
        else:
            draw_text(self.screen, "(no engine selected)",
                      (status_rect.right - 260, status_rect.y + 40),
                      15, DIM_TEXT)

        self._draw_menu_button(self.browse_rect, "Browse Engine",
                               enabled=True, primary=False)
        self._draw_menu_button(self.start_rect, "Start Test",
                               enabled=self.target_path is not None,
                               primary=True)

        draw_text_centered(
            self.screen,
            "Eloify  ·  Built for chess engine developers",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 26),
            13, DIM_TEXT)

    def draw_running(self):
        w = self.worker
        if w is None:
            return
        self._update_animation()
        draw_text(self.screen, "Tournament in Progress", (30, 20), 26, ACCENT, bold=True)
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        elapsed_str = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
        draw_text(self.screen, f"Elapsed  {elapsed_str}", (830, 26), 18, DIM_TEXT)
        draw_text(self.screen, f"Target: {w.target_name}", (30, 60), 20, TEXT_COLOR, bold=True)
        draw_text(self.screen, f"Opponent: {w.opponent_name}  ·  {w.opponent_rating} Elo",
                  (30, 86), 20, DIM_TEXT)
        draw_text(self.screen, f"Game {w.games_played + 1} / {w.total_games}",
                  (830, 60), 18, DIM_TEXT)
        draw_text(self.screen, f"W {w.wins}", (790, 86), 18, WIN_COLOR)
        draw_text(self.screen, f"D {w.draws}", (845, 86), 18, DRAW_COLOR)
        draw_text(self.screen, f"L {w.losses}", (900, 86), 18, LOSS_COLOR)

        last_move = None
        if self.last_move_from is not None and self.last_move_to is not None:
            last_move = (self.last_move_from, self.last_move_to)
        draw_board(self.screen, w.current_fen_shared, BOARD_POS,
                   self.animation, last_move=last_move)
        pygame.draw.rect(self.screen, BORDER,
                         pygame.Rect(BOARD_POS[0] - 2, BOARD_POS[1] - 2,
                                     BOARD_SIZE + 4, BOARD_SIZE + 4),
                         width=2)

        info_panel = pygame.Rect(520, 130, 460, 490)
        draw_rounded_panel(self.screen, info_panel)
        x, y = INFO_POS
        x += 6
        y -= 4

        draw_section(self.screen, "TARGET ENGINE", (x, y), width=200)
        draw_text(self.screen, w.target_name, (x, y + 24), 18, TEXT_COLOR)
        draw_text(self.screen, f"Config: {w.target_config_str}",
                  (x, y + 46), 14, DIM_TEXT)

        draw_section(self.screen, "OPPONENT ENGINE", (x, y + 82), width=200)
        draw_text(self.screen, f"{w.opponent_name}  ({w.opponent_rating})",
                  (x, y + 106), 18, TEXT_COLOR)
        draw_text(self.screen, f"Config: {w.opponent_config_str}",
                  (x, y + 128), 14, DIM_TEXT)

        draw_section(self.screen, "PROGRESS", (x, y + 164), width=420)
        frac = (w.games_played / w.total_games) if w.total_games else 0.0
        bar_rect = pygame.Rect(x, y + 190, 420, 8)
        pygame.draw.rect(self.screen, (45, 50, 62), bar_rect, border_radius=4)
        if frac > 0:
            fill_w = max(2, int(bar_rect.width * frac))
            pygame.draw.rect(self.screen, ACCENT,
                             pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height),
                             border_radius=4)
        draw_text(self.screen, f"{w.games_played} / {w.total_games} games  ({frac:.0%})",
                  (x, y + 204), 14, DIM_TEXT)
        draw_text(self.screen, f"W {w.wins}", (x, y + 226), 18, WIN_COLOR, bold=True)
        draw_text(self.screen, f"D {w.draws}", (x + 70, y + 226), 18, DRAW_COLOR, bold=True)
        draw_text(self.screen, f"L {w.losses}", (x + 140, y + 226), 18, LOSS_COLOR, bold=True)

        draw_section(self.screen, "CURRENT GAME", (x, y + 262), width=420)
        side = "White" if w.target_is_white else "Black"
        dot_cx = x + 8
        dot_cy = y + 296
        dot_color = (245, 245, 245) if w.target_is_white else (15, 15, 15)
        pygame.draw.circle(self.screen, dot_color, (dot_cx, dot_cy), 7)
        pygame.draw.circle(self.screen, BORDER, (dot_cx, dot_cy), 7, width=1)
        draw_text(self.screen, f"Target plays {side}", (x + 22, y + 286), 16, TEXT_COLOR)
        draw_text(self.screen,
                  f"Move {w.current_move_number}   ·   Last: {w.last_move_san or '—'}",
                  (x, y + 310), 16, DIM_TEXT)
        recent = " ".join(w.recent_moves[-8:]) if w.recent_moves else "—"
        draw_text(self.screen, f"Recent: {recent}", (x, y + 334), 14, DIM_TEXT)

        draw_section(self.screen, "LAST RESULT", (x, y + 368), width=420)
        draw_text(self.screen, w.last_game_result or "—",
                  (x, y + 392), 16, TEXT_COLOR)
        draw_text(self.screen, self.status_text, (30, 700), 14, DIM_TEXT)

    def draw_done(self):
        if self.estimated_elo is None or self.error_text:
            draw_text_centered(self.screen, "Test Complete",
                               (WINDOW_WIDTH // 2, 40), 30, ACCENT, bold=True)
            if self.error_text:
                draw_text_centered(self.screen, f"Error: {self.error_text}",
                                   (WINDOW_WIDTH // 2, 100), 20, ERROR_COLOR)
            else:
                draw_text_centered(self.screen, "Could not estimate Elo",
                                   (WINDOW_WIDTH // 2, 100), 26, ERROR_COLOR)
            draw_text_centered(self.screen, "Click anywhere to run another test.",
                               (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40), 16, DIM_TEXT)
            return
        elapsed = time.time() - self.done_start_time if self.done_start_time else 999.0
        if elapsed < REVEAL_DURATION:
            self._draw_mystery_reveal(elapsed)
            return
        if not self.confetti_spawned:
            self._spawn_confetti()
            self.confetti_spawned = True
            if self.celebration_sound:
                try:
                    self.celebration_sound.play()
                except Exception:
                    pass
        pop_elapsed = elapsed - REVEAL_DURATION
        draw_text_centered(self.screen, "Test Complete",
                           (WINDOW_WIDTH // 2, 30), 26, ACCENT, bold=True)
        self._draw_elo_pop(170, pop_elapsed)
        w = self.worker
        if w is not None:
            score = (w.wins + 0.5 * w.draws) / w.games_played if w.games_played else 0.0
            draw_text_centered(self.screen, f"Target: {w.target_name}",
                               (WINDOW_WIDTH // 2, 268), 18, TEXT_COLOR)
            draw_text_centered(
                self.screen,
                f"Games {w.games_played}    W {w.wins}  D {w.draws}  L {w.losses}    Score {score:.1%}",
                (WINDOW_WIDTH // 2, 292), 16, DIM_TEXT)
            draw_text_centered(self.screen, f"Config: {w.target_config_str}",
                               (WINDOW_WIDTH // 2, 314), 14, DIM_TEXT)

            draw_section(self.screen, "PER-OPPONENT RESULTS", (50, 348), width=900)
            row_y = 378
            col_x = [50, 460, 560, 640, 720, 800]
            headers = ["Opponent", "Rating", "W", "D", "L", "Score"]
            hdr_colors = [ACCENT, ACCENT, WIN_COLOR, DRAW_COLOR, LOSS_COLOR, ACCENT]
            for cx, h, c in zip(col_x, headers, hdr_colors):
                draw_text(self.screen, h, (cx, row_y), 15, c, bold=True)
            row_y += 22
            for idx, (name, rating, ww, dd, ll) in enumerate(w.per_opponent_results):
                total = ww + dd + ll
                if total == 0:
                    continue
                pct = (ww + 0.5 * dd) / total * 100.0
                frac = (ww + 0.5 * dd) / total
                if idx % 2 == 0:
                    pygame.draw.rect(self.screen, PANEL,
                                     pygame.Rect(40, row_y - 2,
                                                 WINDOW_WIDTH - 80, 20),
                                     border_radius=3)
                disp = name if len(name) <= 48 else name[:45] + "…"
                draw_text(self.screen, disp, (col_x[0], row_y), 14, TEXT_COLOR)
                draw_text(self.screen, f"{rating}", (col_x[1], row_y), 14, TEXT_COLOR)
                draw_text(self.screen, f"{ww}", (col_x[2], row_y), 14, WIN_COLOR)
                draw_text(self.screen, f"{dd}", (col_x[3], row_y), 14, DRAW_COLOR)
                draw_text(self.screen, f"{ll}", (col_x[4], row_y), 14, LOSS_COLOR)
                if frac > 0.55:
                    sc = WIN_COLOR
                elif frac < 0.45:
                    sc = LOSS_COLOR
                else:
                    sc = DRAW_COLOR
                draw_text(self.screen, f"{pct:5.1f}%", (col_x[5], row_y), 14, sc, bold=True)
                row_y += 22
        draw_text_centered(self.screen, "Click anywhere to run another test.",
                           (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 25), 16, DIM_TEXT)
        self._update_and_draw_confetti()

    def reset(self):
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        try:
            pygame.key.set_repeat()
        except Exception:
            pass
        self.state = "MENU"
        self.target_path = None
        self.status_text = "Select a UCI engine to begin."
        self.estimated_elo = None
        self.estimate_kind = None
        self.confidence = None
        self.error_text = None
        self.worker = None
        self.animation = None
        self.last_animated_fen = chess.STARTING_FEN
        self.last_animated_counter = 0
        self.last_move_from = None
        self.last_move_to = None
        self.done_start_time = None
        self.confetti = []
        self.confetti_spawned = False
        self._elo_surface_cache = None
        self.last_games_played = 0
        self.last_wins         = 0
        self.last_draws        = 0
        self.last_losses       = 0
        self.dragging_slider   = None
        self.settings_snapshot = None
        self._keys_down = set()

    def shutdown(self):
        if self.worker and self.worker.is_alive():
            self.worker.running = False
            self.worker.join(timeout=2)
        try:
            pygame.key.set_repeat()
        except Exception:
            pass
        pygame.quit()
        sys.exit()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = EloifyApp()
    app.run()