import pygame
import chess
import chess.engine
import threading
import queue
import time
import math
import os
import io
import stat
import sys
import subprocess
import random
import array
import wave
import platform
import warnings
import re
import tempfile
import traceback
from collections import deque
from datetime import datetime
import eloify_features as ef

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
FOX_CHESS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines", "fox-chess")
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio")
AUDIO_SOUND_FILES = {
    "castle":     "castle.mp3",
    "game-start": "game-start.mp3",
    "game-end":   "game-end.mp3",
    "move-self":  "move-self.mp3",
    "move-check": "move-check.mp3",
    "promote":    "promote.mp3",
}

def detect_fox_cpu():
    """Return usable instruction flags and CPU identity; fail closed on detection errors."""
    try:
        from cpuinfo import get_cpu_info
        info = get_cpu_info()
        if platform.machine().lower() not in ("amd64", "x86_64"):
            return {}
        flags = set(info.get("flags", []))
        if sys.platform == "win32":
            # Windows checks include OS extended-register state support, not just CPUID.
            import ctypes
            supported = ctypes.windll.kernel32.IsProcessorFeaturePresent
            supported.argtypes = [ctypes.c_uint]
            supported.restype = ctypes.c_int
            if not supported(40):  # PF_AVX2_INSTRUCTIONS_AVAILABLE
                flags.discard("avx2")
            if not supported(41):  # PF_AVX512F_INSTRUCTIONS_AVAILABLE
                flags = {flag for flag in flags if not flag.startswith("avx512")}
        elif sys.platform != "linux":
            # Only Windows and Linux detection is supported for these x86 builds.
            return {}
        return dict(info, flags=flags)
    except Exception as exc:
        warnings.warn(f"Cannot detect FoxChess CPU support: {exc}. Install requirements.txt.")
        return {}


def fox_build_order(cpu):
    """Prefer fast PEXT only on CPUs known to have hardware BMI2 (AMD Zen 3+)."""
    flags = set(cpu.get("flags", []))
    if "avx2" not in flags:
        return []
    vendor = cpu.get("vendor_id", "")
    family = cpu.get("family", 0)
    fast_bmi2 = "bmi2" in flags and (
        vendor == "GenuineIntel" or
        (vendor == "AuthenticAMD" and isinstance(family, int) and family >= 0x19)
    )
    order = ["avx2-bmi2", "avx2"] if fast_bmi2 else ["avx2"]
    # Conservatively require the common AVX-512 subsets and fast BMI2: build
    # filenames alone do not describe every instruction emitted by the compiler.
    if fast_bmi2 and {"avx512f", "avx512bw", "avx512dq", "avx512vl"} <= flags:
        order.insert(0, "avx512")
    return order


def fox_opponents(cpu=None, engine_dir=FOX_CHESS_DIR):
    """Choose one existing, compatible executable per version, never duplicate ratings."""
    order = fox_build_order(detect_fox_cpu() if cpu is None else cpu)
    opponents = []
    for prefix, rating in (("v1.0", 2740), ("v1.1", 2870),
                           ("foxchess-current", 3060)):  # v1.2/current
        for build in order:
            path = os.path.join(engine_dir, f"{prefix}-{build}.exe")
            if os.path.isfile(path):
                opponents.append((path, rating))
                break
        else:
            warnings.warn(f"Skipping FoxChess {prefix}: no compatible installed build.")
    return opponents


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
    *fox_opponents(),
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

# Automatic >3600 Elo time-odds extension for top engines.
# Multiplies the strongest available engine's per-move budget to create fixed
# high-Elo tiers (e.g. 3740–4010 Elo when anchored on Stockfish 19 at 3660).
HIGH_ELO_TIME_ODDS_TIERS = (
    (2,  80),
    (4,  155),
    (8,  225),
    (16, 290),
    (32, 350),
)
HIGH_ELO_TRIGGER_RATING = 3550
HIGH_ELO_TOP_BRACKET = 3500
HIGH_ELO_MIN_TOP_SCORE = 0.50
HIGH_ELO_DEFAULT_ANCHOR_RATING = 3660

# Balanced paired openings used only in the >3600 extension (each played with
# both colors per tier so top engines do not repeat identical startpos draws).
HIGH_ELO_OPENINGS = (
    ("Sicilian Najdorf",       ("e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6")),
    ("Ruy Lopez Open",         ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1", "f6e4")),
    ("French Winawer",         ("e2e4", "e7e6", "d2d4", "d7d5", "b1c3", "f8b4", "e4e5", "c7c5", "a2a3", "b4c3", "b2c3", "g8e7")),
    ("Caro-Kann Advance",      ("e2e4", "c7c6", "d2d4", "d7d5", "e4e5", "c8f5", "g1f3", "e7e6", "f1e2", "c6c5")),
    ("Nimzo-Indian",           ("d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4", "e2e3", "e8g8", "f1d3", "d7d5")),
    ("King's Indian",          ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4", "d7d6", "g1f3", "e8g8")),
    ("Gruenfeld Exchange",     ("d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5", "c4d5", "f6d5", "e2e4", "d5c3", "b2c3", "f8g7")),
    ("Semi-Slav Meran",        ("d2d4", "d7d5", "c2c4", "c7c6", "g1f3", "g8f6", "b1c3", "e7e6", "e2e3", "b8d7")),
    ("Queen's Gambit Ragozin", ("d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "g1f3", "f8b4", "c1g5", "h7h6")),
    ("Catalan Open",           ("d2d4", "g8f6", "c2c4", "e7e6", "g2g3", "d7d5", "f1g2", "d5c4", "g1f3", "f8e7")),
    ("English Four Knights",   ("c2c4", "e7e5", "b1c3", "g8f6", "g1f3", "b8c6", "g2g3", "d7d5", "c4d5", "f6d5")),
    ("Sicilian Scheveningen",  ("e2e4", "c7c5", "g1f3", "e7e6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "d7d6")),
)

RESULTS_VISIBLE_ROWS = 13

# ----------------------------------------------------------------------
# UI CONSTANTS  — refined palette
# ----------------------------------------------------------------------
WINDOW_WIDTH, WINDOW_HEIGHT = 1240, 780
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

BOARD_SIZE = 440
SQUARE_SIZE = BOARD_SIZE // 8
BOARD_POS = (56, 134)
INFO_POS = (514, 92)

BOARD_LIGHT = (238, 216, 183)
BOARD_DARK  = (171, 122, 89)
_ACTIVE_BOARD_LIGHT = BOARD_LIGHT
_ACTIVE_BOARD_DARK  = BOARD_DARK
_ACTIVE_PIECE_STYLE = "classic_2tone"
_ACTIVE_SHOW_COORDS = True

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

# Browse dialog layout (centered in WINDOW_WIDTH x WINDOW_HEIGHT)
_BROWSE_X = (WINDOW_WIDTH - 900) // 2
_BROWSE_Y = (WINDOW_HEIGHT - 620) // 2
BROWSE_PANEL             = pygame.Rect(_BROWSE_X, _BROWSE_Y, 900, 620)
BROWSE_FIELD             = pygame.Rect(_BROWSE_X + 30, _BROWSE_Y + 60, 840, 38)
BROWSE_UP_RECT           = pygame.Rect(_BROWSE_X + 30, _BROWSE_Y + 112, 60, 30)
BROWSE_HOME_RECT         = pygame.Rect(_BROWSE_X + 98, _BROWSE_Y + 112, 72, 30)
BROWSE_REFRESH_RECT      = pygame.Rect(_BROWSE_X + 178, _BROWSE_Y + 112, 84, 30)
BROWSE_SHOW_HIDDEN_RECT  = pygame.Rect(_BROWSE_X + 614, _BROWSE_Y + 112, 256, 30)
BROWSE_SHOW_HIDDEN_LABEL = "Show hidden folders/files"
BROWSE_LIST              = pygame.Rect(_BROWSE_X + 30, _BROWSE_Y + 154, 840, 356)
BROWSE_INFO_Y            = _BROWSE_Y + 522
BROWSE_CANCEL_RECT       = pygame.Rect(_BROWSE_X + 690, _BROWSE_Y + 552, 90, 38)
BROWSE_OPEN_RECT         = pygame.Rect(_BROWSE_X + 790, _BROWSE_Y + 552, 90, 38)
BROWSE_ROW_HEIGHT        = 24
BROWSE_FIELD_PADDING     = 8

FILE_ATTRIBUTE_HIDDEN = getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 0x2)
UF_HIDDEN = getattr(stat, "UF_HIDDEN", 0x8000)


def _is_hidden_entry(entry):
    """Return True when a directory entry or path is hidden on Windows, macOS, or Linux."""
    name = entry.name if hasattr(entry, "name") else os.path.basename(str(entry))
    if name in ("", ".", ".."):
        return False
    if name.startswith("."):
        return True
    try:
        st = (entry.stat(follow_symlinks=False)
              if hasattr(entry, "stat")
              else os.stat(entry, follow_symlinks=False))
    except OSError:
        return False
    if getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_HIDDEN:
        return True
    if getattr(st, "st_flags", 0) & UF_HIDDEN:
        return True
    return False

SELECTION_BG   = (55, 95, 135)
FIELD_BG       = (20, 24, 30)
FIELD_BORDER   = (70, 76, 90)
LIST_BG        = (26, 30, 38)
LIST_ROW_HOVER = (40, 46, 56)
LIST_ROW_SEL   = (50, 90, 70)

# Error report layout and default on-disk destination.
ERROR_REPORT_RECT = pygame.Rect(40, 150, WINDOW_WIDTH - 80, WINDOW_HEIGHT - 240)
ERROR_COPY_RECT = pygame.Rect(40, WINDOW_HEIGHT - 65, 200, 38)
ERROR_BACK_RECT = pygame.Rect(WINDOW_WIDTH - 240, WINDOW_HEIGHT - 65, 200, 38)
ERROR_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

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
def _windows_clipboard_api():
    """Declare Win32 handle/pointer types explicitly (ctypes defaults to int)."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    signatures = (
        (user32.OpenClipboard, [wintypes.HWND], wintypes.BOOL),
        (user32.CloseClipboard, [], wintypes.BOOL),
        (user32.EmptyClipboard, [], wintypes.BOOL),
        (user32.GetClipboardData, [wintypes.UINT], wintypes.HANDLE),
        (user32.SetClipboardData, [wintypes.UINT, wintypes.HANDLE], wintypes.HANDLE),
        (kernel32.GlobalAlloc, [wintypes.UINT, ctypes.c_size_t], wintypes.HGLOBAL),
        (kernel32.GlobalLock, [wintypes.HGLOBAL], ctypes.c_void_p),
        (kernel32.GlobalUnlock, [wintypes.HGLOBAL], wintypes.BOOL),
        (kernel32.GlobalFree, [wintypes.HGLOBAL], wintypes.HGLOBAL),
    )
    for function, args, result in signatures:
        function.argtypes = args
        function.restype = result
    return user32, kernel32


def _get_clipboard_text():
    if sys.platform == "win32":
        try:
            import ctypes
            user32, kernel32 = _windows_clipboard_api()
            if not user32.OpenClipboard(None):
                raise RuntimeError("OpenClipboard failed")
            try:
                handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if not handle:
                    return ""
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    raise RuntimeError("GlobalLock failed")
                try:
                    return ctypes.wstring_at(ptr)
                finally:
                    kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        except Exception:
            commands = [["powershell", "-NoProfile", "-Command",
                         "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                         "Get-Clipboard -Raw"]]
    elif sys.platform == "darwin":
        commands = [["pbpaste"]]
    else:
        commands = []
        if os.environ.get("WAYLAND_DISPLAY"):
            commands.append(["wl-paste", "--no-newline", "--type", "text"])
        commands.extend([["xclip", "-selection", "clipboard", "-o"],
                         ["xsel", "-b", "-o"]])
    for command in commands:
        try:
            return subprocess.check_output(
                command, stderr=subprocess.DEVNULL, timeout=2
            ).decode("utf-8-sig")
        except (OSError, subprocess.SubprocessError, UnicodeError):
            continue
    # SDL's clipboard works on X11 even without external clipboard utilities.
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
        data = pygame.scrap.get(pygame.SCRAP_TEXT)
        return data.rstrip(b"\x00").decode("utf-8") if data else ""
    except Exception:
        return ""


def _set_clipboard_text(text):
    if sys.platform == "win32":
        try:
            import ctypes
            user32, kernel32 = _windows_clipboard_api()
            data = text.encode("utf-16-le") + b"\x00\x00"
            # A real owner window is required: EmptyClipboard after opening with
            # NULL makes SetClipboardData fail according to the Win32 contract.
            owner = pygame.display.get_wm_info().get("window")
            if not owner or not user32.OpenClipboard(owner):
                return False
            handle = None
            try:
                handle = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
                if not handle:
                    return False
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return False
                try:
                    ctypes.memmove(ptr, data, len(data))
                finally:
                    kernel32.GlobalUnlock(handle)
                if not user32.EmptyClipboard():
                    return False
                if not user32.SetClipboardData(13, handle):
                    return False
                handle = None  # Windows now owns the allocation; do not free it.
                return True
            finally:
                if handle:
                    kernel32.GlobalFree(handle)
                user32.CloseClipboard()
        except Exception:
            return False
    elif sys.platform == "darwin":
        commands = [["pbcopy"]]
    else:
        commands = []
        if os.environ.get("WAYLAND_DISPLAY"):
            commands.append(["wl-copy", "--type", "text/plain;charset=utf-8"])
        commands.extend([["xclip", "-selection", "clipboard"],
                         ["xsel", "-b", "-i"]])
    for command in commands:
        try:
            subprocess.run(command, input=text.encode("utf-8"),
                           stderr=subprocess.DEVNULL, check=True, timeout=2)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.set_mode(pygame.SCRAP_CLIPBOARD)
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8") + b"\x00")
        return True
    except Exception:
        return False

# ----------------------------------------------------------------------
# ENGINE ERROR DIAGNOSTICS
# ----------------------------------------------------------------------
def _exception_message(exc):
    message = str(exc).strip()
    if not message:
        message = ("Engine did not respond before the command timeout."
                   if isinstance(exc, TimeoutError) else "No error message supplied.")
    return f"{type(exc).__name__}: {message}"


def _engine_failure_details(exc, engine):
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    protocol = getattr(engine, "protocol", None)
    recent = getattr(protocol, "diagnostics", ())
    # Copy on the protocol's deque before formatting, since its event loop may
    # still be receiving output while the worker handles the failure.
    recent = recent.copy() if isinstance(recent, deque) else recent
    if recent:
        details += "\nRecent UCI traffic / engine stderr:\n" + "\n".join(recent) + "\n"
    return details


def _save_error_log(report):
    """Save a unique UTF-8 report, falling back if the install is read-only."""
    directories = (ERROR_LOG_DIR, os.path.expanduser("~/.eloify/logs"),
                   os.path.join(tempfile.gettempdir(), "Eloify", "logs"))
    failures = []
    for directory in dict.fromkeys(directories):
        path = None
        try:
            os.makedirs(directory, exist_ok=True)
            fd, path = tempfile.mkstemp(
                prefix=datetime.now().strftime("eloify-error-%Y%m%d-%H%M%S-"),
                suffix=".log", dir=directory)
            with os.fdopen(fd, "w", encoding="utf-8", errors="backslashreplace") as log:
                log.write(report)
            return os.path.abspath(path), None
        except OSError as exc:
            failures.append(f"{directory}: {_exception_message(exc)}")
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass
    return None, "\n".join(failures)


def _wrap_error_text(text, font, width):
    """Pixel-wrap report lines, including long unbroken executable paths."""
    lines = []
    for raw_line in text.splitlines():
        remaining = raw_line.expandtabs(4)
        while remaining and font.size(remaining)[0] > width:
            lo, hi = 1, len(remaining)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if font.size(remaining[:mid])[0] <= width:
                    lo = mid
                else:
                    hi = mid - 1
            cut = remaining.rfind(" ", 0, lo + 1)
            if cut <= 0:
                cut = lo
            lines.append(remaining[:cut])
            remaining = remaining[cut:].lstrip()
        lines.append(remaining)
    return lines


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
            exp = max(-100.0, min(100.0, (opp_rating - target_elo) / 400.0))
            p = 1.0 / (1.0 + 10.0 ** exp)
            s += p * n
        return s

    max_rating = max(r for (r, _, _, _) in per_opponent)
    min_rating = min(r for (r, _, _, _) in per_opponent)

    if total_score >= total_games - 1e-9:
        return ("lower_bound", max_rating + 400)
    if total_score <= 1e-9:
        return ("upper_bound", min_rating - 400)

    lo = min(0.0, float(min_rating) - 1500.0)
    hi = max(5000.0, float(max_rating) + 1500.0)
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


def format_time_multiplier(multiplier):
    mult = float(multiplier)
    return f"{int(mult)}x" if mult.is_integer() else f"{mult:g}x"


def _normalize_opponent_results(per_opponent_results):
    pool = []
    for row in per_opponent_results:
        if len(row) == 5:
            _, r, w, d, l = row
        else:
            r, w, d, l = row
        if w + d + l > 0:
            pool.append((r, w, d, l))
    return pool


def should_run_high_elo_extension(per_opponent_results):
    """Return True when standard-pool results indicate a ~3600+ top engine."""
    pool = _normalize_opponent_results(per_opponent_results)
    if not pool:
        return False
    estimate = estimate_elo_vs_pool(pool)
    if estimate is None or estimate[0] == "upper_bound":
        return False
    kind, elo = estimate

    top_pool = [(r, w, d, l) for (r, w, d, l) in pool if r >= HIGH_ELO_TOP_BRACKET]
    if top_pool:
        top_games = sum(w + d + l for _, w, d, l in top_pool)
        top_score = sum(w + 0.5 * d for _, w, d, l in top_pool)
        if top_games == 0 or (top_score / top_games) < HIGH_ELO_MIN_TOP_SCORE - 1e-9:
            return False
    else:
        max_r = max(r for r, _, _, _ in pool)
        near_top = [(r, w, d, l) for (r, w, d, l) in pool if r >= max_r - 100]
        nt_games = sum(w + d + l for _, w, d, l in near_top)
        nt_score = sum(w + 0.5 * d for _, w, d, l in near_top)
        if kind != "lower_bound" and (nt_games == 0 or (nt_score / nt_games) < 0.75 - 1e-9):
            return False

    return kind == "lower_bound" or elo >= HIGH_ELO_TRIGGER_RATING - 1e-9


def select_high_elo_anchor(working_opponents, adjudicator_path=None,
                           adjudicator_available=False, configured_opponents=()):
    """Choose the strongest non-Maia engine available for >3600 time-odds tiers."""
    best_opp = None
    for path, rating in working_opponents:
        if path and (best_opp is None or rating >= best_opp[1]):
            best_opp = (path, rating)

    if best_opp is not None and best_opp[1] >= HIGH_ELO_TOP_BRACKET:
        return best_opp

    if adjudicator_available and adjudicator_path and not is_maia_engine(None, adjudicator_path):
        norm_adj = os.path.normcase(os.path.normpath(adjudicator_path))
        matched_ratings = [
            r for p, r in configured_opponents
            if p and os.path.normcase(os.path.normpath(p)) == norm_adj
        ]
        adj_rating = max(matched_ratings) if matched_ratings else HIGH_ELO_DEFAULT_ANCHOR_RATING
        if best_opp is None or adj_rating >= best_opp[1]:
            return (adjudicator_path, adj_rating)

    return best_opp


def build_high_elo_tiers(anchor_path, anchor_rating, tiers=None):
    """Build fixed >3600 Elo opponent tiers as (path, calibrated_elo, time_multiplier)."""
    if not anchor_path:
        return []
    if tiers is None:
        tiers = HIGH_ELO_TIME_ODDS_TIERS
    threshold = max(3600, anchor_rating)
    return [
        (anchor_path, int(anchor_rating + bonus), float(mult))
        for mult, bonus in tiers
        if anchor_rating + bonus > threshold
    ]


_UNSET = object()


def get_pool_max_extended_elo(opponents=None, adjudicator_path=_UNSET, tiers=None):
    """Return (extension_tier_count, max_elo) for menu summary display."""
    if opponents is None:
        opponents = OPPONENTS
    if adjudicator_path is _UNSET:
        adjudicator_path = ADJUDICATOR_PATH
    if tiers is None:
        tiers = HIGH_ELO_TIME_ODDS_TIERS
    non_maia = [(p, r) for p, r in opponents if p and not is_maia_engine(None, p)]
    anchor = select_high_elo_anchor(
        non_maia,
        adjudicator_path=adjudicator_path,
        adjudicator_available=bool(adjudicator_path),
        configured_opponents=opponents,
    )
    base_max = max((r for _, r in opponents), default=0)
    if anchor is None:
        return 0, base_max
    ext_tiers = build_high_elo_tiers(anchor[0], anchor[1], tiers=tiers)
    if not ext_tiers:
        return 0, base_max
    return len(ext_tiers), max(base_max, max(r for _, r, _ in ext_tiers))


def select_extension_openings(tier_count, games_per_opponent=None,
                              openings=None, rng=None):
    """Assign paired openings per tier so White and Black play the same book line."""
    if games_per_opponent is None:
        games_per_opponent = GAMES_PER_OPPONENT
    if openings is None:
        openings = HIGH_ELO_OPENINGS
    if tier_count <= 0 or games_per_opponent <= 0 or not openings:
        return [[None] * max(0, games_per_opponent) for _ in range(max(0, tier_count))]

    pairs_per_tier = games_per_opponent // 2
    total_pairs = tier_count * pairs_per_tier
    chooser = rng if rng is not None else random
    deck = []
    while len(deck) < total_pairs:
        batch = list(openings)
        chooser.shuffle(batch)
        if deck and len(batch) > 1 and batch[0] == deck[-1]:
            batch[0], batch[-1] = batch[-1], batch[0]
        deck.extend(batch)

    schedule = []
    pair_cursor = 0
    for _ in range(tier_count):
        tier_games = []
        for _ in range(pairs_per_tier):
            opening = deck[pair_cursor]
            pair_cursor += 1
            tier_games.append(opening)
            tier_games.append(opening)
        if games_per_opponent % 2 == 1:
            # Leave any unpaired odd game on standard startpos for fairness.
            tier_games.append(None)
        schedule.append(tier_games)
    return schedule

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
# Old engines can hang in their own thread teardown after receiving quit.
ENGINE_QUIT_TIMEOUT = 1.0
LEGACY_MOVETIME_GRACE = 0.1


class CompatibleUciProtocol(chess.engine.UciProtocol):
    """Keep SF 2.2-era timer delays from overrunning fixed-time searches.

    Still send the normal `go movetime`: the engine may finish early as usual.
    Arm a fallback `stop` only once `go` is actually sent (not while configuring
    hash/threads). Everything runs on python-chess's protocol event loop.
    """

    def __init__(self):
        super().__init__()
        self._movetime_stop = None
        self.diagnostics = deque(maxlen=80)
        self.latest_nps = 0
        self.latest_depth = 0
        self.latest_score_cp = None
        self.latest_score_mate = None

    def _cancel_movetime_stop(self):
        if self._movetime_stop is not None:
            self._movetime_stop.cancel()
            self._movetime_stop = None

    def _stop_overdue_search(self):
        self._movetime_stop = None
        self.send_line("stop")

    def send_line(self, line):
        self.diagnostics.append(">> " + line[:2000])
        tokens = line.split()
        if tokens and tokens[0] in ("go", "stop", "quit"):
            self._cancel_movetime_stop()
            if tokens[0] == "go":
                self.latest_score_cp = None
                self.latest_score_mate = None
        super().send_line(line)
        name = self.id.get("name", "")
        if (tokens and tokens[0] == "go" and "movetime" in tokens
                and "ponder" not in tokens and "infinite" not in tokens
                and re.match(r"^Stockfish\s+2\.2(?:\.[12])?(?=\s|$)", name, re.I)):
            milliseconds = int(tokens[tokens.index("movetime") + 1])
            self._movetime_stop = self.loop.call_later(
                milliseconds / 1000.0 + LEGACY_MOVETIME_GRACE,
                self._stop_overdue_search)

    def line_received(self, line):
        self.diagnostics.append("<< " + line[:2000])
        tokens = line.split()
        if tokens[:1] == ["info"]:
            for i, tok in enumerate(tokens):
                if tok == "nps" and i + 1 < len(tokens):
                    try:
                        self.latest_nps = int(tokens[i + 1])
                    except ValueError:
                        pass
                elif tok == "depth" and i + 1 < len(tokens):
                    try:
                        self.latest_depth = int(tokens[i + 1])
                    except ValueError:
                        pass
                elif tok == "score" and i + 2 < len(tokens):
                    kind = tokens[i + 1]
                    try:
                        val = int(tokens[i + 2])
                        if kind == "cp":
                            self.latest_score_cp = val
                            self.latest_score_mate = None
                        elif kind == "mate":
                            self.latest_score_mate = val
                            self.latest_score_cp = 10000 - abs(val) * 50 if val > 0 else -10000 + abs(val) * 50
                    except ValueError:
                        pass
        elif tokens[:1] == ["bestmove"]:
            self._cancel_movetime_stop()
        super().line_received(line)

    def error_line_received(self, line):
        self.diagnostics.append("stderr: " + line[:2000])
        super().error_line_received(line)

    def connection_lost(self, exc):
        self._cancel_movetime_stop()
        super().connection_lost(exc)


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
        # Cinnamon 1.x advertises up to 32768 MB, but its legacy allocator
        # asserts when either of two large calloc() calls fails. The 32-bit
        # 1.2c build cannot reliably allocate a ~2 GB table on Windows. Its
        # signed-int size arithmetic also makes multi-GB requests unsafe.
        # Keep this workaround engine-specific; modern engines retain the
        # requested hash budget. Smaller user budgets are left unchanged.
        name = (getattr(engine, "id", None) or {}).get("name", "")
        if re.match(r"^Cinnamon\s+1(?:\.\d+[a-z]?)?(?=\s|$)", name, re.I):
            h = min(h, 256)
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
    # Legacy Stockfish otherwise busy-spins idle split-point workers. This is
    # particularly costly with short searches and several engines alive.
    if "Use Sleeping Threads" in opts:
        s["Use Sleeping Threads"] = True

    if not is_adjudicator and path is not None and is_maia_engine(engine, path):
        s["NodesPerSecond"] = 1

    return s

def apply_engine_config(engine, settings):
    if not settings:
        return
    try:
        engine.configure(settings)
    except (chess.engine.EngineTerminatedError, TimeoutError):
        raise
    except Exception:
        for k, v in settings.items():
            try:
                engine.configure({k: v})
            except (chess.engine.EngineTerminatedError, TimeoutError):
                raise
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
# AUDIO LOADING & FALLBACK SYNTHESIS
# ----------------------------------------------------------------------
def _samples_to_sound(samples, sr=22050):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    buf.seek(0)
    return pygame.mixer.Sound(file=buf)


def _resolve_audio_file(filename, audio_dir=None):
    base_dir = AUDIO_DIR if audio_dir is None else audio_dir
    exact = os.path.join(base_dir, filename)
    if os.path.isfile(exact):
        return exact
    if os.path.isdir(base_dir):
        target_lower = filename.lower()
        try:
            for entry in os.listdir(base_dir):
                if entry.lower() == target_lower:
                    candidate = os.path.join(base_dir, entry)
                    if os.path.isfile(candidate):
                        return candidate
        except OSError:
            pass
    return None


def _load_sound_file(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        with open(path, "rb") as f:
            return pygame.mixer.Sound(file=io.BytesIO(f.read()))


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
    return _samples_to_sound(samples, sr=sr)


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
    return _samples_to_sound(samples, sr=sr)


def _generate_move_sound(duration=0.05, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    for i in range(n):
        t = i / sr
        env = math.exp(-t * 90)
        val = math.sin(2 * math.pi * 620 * t) * env * 0.55
        val += math.sin(2 * math.pi * 260 * t) * env * 0.25
        samples[i] = int(max(-1.0, min(1.0, val)) * 12000)
    return _samples_to_sound(samples, sr=sr)


def _generate_castle_sound(duration=0.11, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    for i in range(n):
        t = i / sr
        val = 0.0
        env1 = math.exp(-t * 85)
        val += math.sin(2 * math.pi * 580 * t) * env1 * 0.50
        val += math.sin(2 * math.pi * 240 * t) * env1 * 0.25
        if t >= 0.045:
            dt = t - 0.045
            env2 = math.exp(-dt * 85)
            val += math.sin(2 * math.pi * 700 * dt) * env2 * 0.50
            val += math.sin(2 * math.pi * 290 * dt) * env2 * 0.25
        samples[i] = int(max(-1.0, min(1.0, val)) * 13000)
    return _samples_to_sound(samples, sr=sr)


def _generate_promote_sound(duration=0.22, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 587.33), (0.06, 880.00)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.006)
                env = attack * math.exp(-dt * 18)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.40
        samples[i] = int(max(-1.0, min(1.0, val)) * 16000)
    return _samples_to_sound(samples, sr=sr)


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
    return _samples_to_sound(samples, sr=sr)


def _generate_game_start_sound(duration=0.18, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 440.00), (0.06, 587.33)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.008)
                env = attack * math.exp(-dt * 20)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.35
        samples[i] = int(max(-1.0, min(1.0, val)) * 16000)
    return _samples_to_sound(samples, sr=sr)


def _generate_game_end_sound(duration=0.35, sr=22050):
    n = int(duration * sr)
    samples = array.array('h', bytes(n * 2))
    notes = [(0.00, 523.25), (0.10, 659.25)]
    for i in range(n):
        t = i / sr
        val = 0.0
        for start, freq in notes:
            if t >= start:
                dt = t - start
                attack = min(1.0, dt / 0.01)
                env = attack * math.exp(-dt * 9)
                val += math.sin(2 * math.pi * freq * dt) * env * 0.35
        samples[i] = int(max(-1.0, min(1.0, val)) * 18000)
    return _samples_to_sound(samples, sr=sr)


_SOUND_FALLBACK_GENERATORS = {
    "castle":     _generate_castle_sound,
    "game-start": _generate_game_start_sound,
    "game-end":   _generate_game_end_sound,
    "move-self":  _generate_move_sound,
    "move-check": _generate_check_sound,
    "promote":    _generate_promote_sound,
}


def _load_game_sounds(audio_dir=None, sound_files=None):
    base_dir = AUDIO_DIR if audio_dir is None else audio_dir
    mapping = AUDIO_SOUND_FILES if sound_files is None else sound_files
    loaded = {}
    missing = []
    for key, filename in mapping.items():
        resolved = _resolve_audio_file(filename, audio_dir=base_dir)
        snd = None
        if resolved is not None:
            try:
                snd = _load_sound_file(resolved)
            except Exception as exc:
                warnings.warn(f"Could not load sound '{resolved}': {exc}")
        if snd is None:
            missing.append(filename)
            gen = _SOUND_FALLBACK_GENERATORS.get(key)
            if gen is not None:
                try:
                    snd = gen()
                except Exception:
                    snd = None
        loaded[key] = snd
    if missing:
        warnings.warn(
            f"Missing or unreadable audio files in '{base_dir}' "
            f"({', '.join(missing)}); using built-in fallback sounds."
        )
    return loaded

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
    if not pygame.font.get_init():
        pygame.font.init()
        _FONT_CACHE.clear()
        _TEXT_CACHE.clear()
    key = (name, size, bold)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = pygame.font.SysFont(name, size, bold=bold)
        _FONT_CACHE[key] = f
    try:
        f.get_height()
    except Exception:
        _FONT_CACHE.clear()
        _TEXT_CACHE.clear()
        pygame.font.init()
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
    if not pygame.font.get_init():
        pygame.font.init()
        _PIECE_FONT_CACHE.clear()
        _PIECE_CACHE.clear()
    if size in _PIECE_FONT_CACHE:
        cached = _PIECE_FONT_CACHE[size]
        try:
            cached.get_height()
            return cached
        except Exception:
            _PIECE_FONT_CACHE.clear()
            _PIECE_CACHE.clear()
            pygame.font.init()
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
def _get_piece_surface(symbol, size, style=None):
    active_style = style or globals().get("_ACTIVE_PIECE_STYLE", "classic_2tone")
    accent = globals().get("ACCENT", (100, 200, 160))
    key = (symbol, size, active_style, accent)
    surf = _PIECE_SURFACE_CACHE.get(key)
    if surf is not None:
        return surf
    _ef = globals().get("ef")
    if _ef is not None:
        out = _ef.render_styled_piece(
            symbol,
            size,
            style=active_style,
            piece_font_getter=_get_piece_font,
            text_font_getter=lambda sz, bold=False: _get_font(_FONT_FAMILY, sz, bold=bold),
            accent=accent,
        )
        _PIECE_SURFACE_CACHE[key] = out
        return out
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

def _sq_to_center_px(square, pos, sq_size=None, flipped=False):
    sq_sz = sq_size or SQUARE_SIZE
    if flipped:
        row = square // 8
        col = 7 - (square % 8)
    else:
        row = 7 - (square // 8)
        col = square % 8
    return (pos[0] + col * sq_sz + sq_sz // 2,
            pos[1] + row * sq_sz + sq_sz // 2)

def _draw_piece_at(surface, symbol, cx, cy, sq_size=None, style=None):
    sq_sz = sq_size or SQUARE_SIZE
    size = int(sq_sz * 0.85)
    surf = _get_piece_surface(symbol, size, style=style)
    surface.blit(surf, surf.get_rect(center=(int(cx), int(cy))))

# ----------------------------------------------------------------------
# BOARD BACKGROUND + LAST-MOVE HIGHLIGHT CACHES
# ----------------------------------------------------------------------
_BOARD_BG_CACHE = {}
def _get_board_bg(size, light_col=None, dark_col=None, show_coords=None, flipped=False):
    lcol = tuple(light_col or globals().get("_ACTIVE_BOARD_LIGHT", BOARD_LIGHT))
    dcol = tuple(dark_col or globals().get("_ACTIVE_BOARD_DARK", BOARD_DARK))
    coords = (globals().get("_ACTIVE_SHOW_COORDS", True)
              if show_coords is None else bool(show_coords))
    key = (size, lcol, dcol, coords, bool(flipped))
    surf = _BOARD_BG_CACHE.get(key)
    if surf is not None:
        return surf
    if len(_BOARD_BG_CACHE) > 48:
        _BOARD_BG_CACHE.clear()
    sq = size // 8
    surf = pygame.Surface((size, size))
    if pygame.display.get_surface() is not None:
        surf = surf.convert()
    coord_font = _get_font(_FONT_FAMILY, max(10, sq // 5), bold=True)
    for row in range(8):
        for col in range(8):
            is_light = (row + col) % 2 == 0
            color = lcol if is_light else dcol
            rect = pygame.Rect(col * sq, row * sq, sq, sq)
            pygame.draw.rect(surf, color, rect)
            pygame.draw.rect(surf, tuple(max(0, c - 18) for c in color),
                             rect, width=1)
            if coords:
                coord_color = dcol if is_light else lcol
                if col == 0:
                    rank = str(row + 1) if flipped else str(8 - row)
                    s = coord_font.render(rank, True, coord_color)
                    surf.blit(s, (col * sq + 3, row * sq + 2))
                if row == 7:
                    file_letter = chr(ord('h') - col) if flipped else chr(ord('a') + col)
                    s = coord_font.render(file_letter, True, coord_color)
                    surf.blit(s, (col * sq + sq - s.get_width() - 3,
                                  row * sq + sq - s.get_height() - 2))
    _BOARD_BG_CACHE[key] = surf
    return surf

_LAST_MOVE_HL = {}
def _get_last_move_highlight(sq_size=None):
    sq_sz = sq_size or SQUARE_SIZE
    hl = _LAST_MOVE_HL.get(sq_sz)
    if hl is None:
        s = pygame.Surface((sq_sz, sq_sz), pygame.SRCALPHA)
        s.fill((255, 220, 100, 72))
        _LAST_MOVE_HL[sq_sz] = s
        hl = s
    return hl

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

def draw_board(surface, board_fen, pos, animation=None, last_move=None,
               flipped=False, show_coords=None, light_col=None, dark_col=None,
               piece_style=None, board_size=None):
    bsize = board_size or BOARD_SIZE
    sq_sz = bsize // 8
    board = _get_board(board_fen)
    surface.blit(
        _get_board_bg(bsize, light_col=light_col, dark_col=dark_col,
                      show_coords=show_coords, flipped=flipped),
        pos,
    )
    if last_move is not None:
        hl = _get_last_move_highlight(sq_sz)
        for sq in last_move:
            if sq is None:
                continue
            if flipped:
                row = sq // 8
                col = 7 - (sq % 8)
            else:
                row = 7 - (sq // 8)
                col = sq % 8
            surface.blit(hl, (pos[0] + col * sq_sz,
                              pos[1] + row * sq_sz))
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
        cx, cy = _sq_to_center_px(square, pos, sq_size=sq_sz, flipped=flipped)
        _draw_piece_at(surface, piece.symbol(), cx, cy, sq_size=sq_sz, style=piece_style)
    if animating:
        t = animation.progress()
        if animation.captured_square is not None and animation.captured_symbol is not None:
            cx, cy = _sq_to_center_px(animation.captured_square, pos, sq_size=sq_sz, flipped=flipped)
            _draw_piece_at(surface, animation.captured_symbol, cx, cy, sq_size=sq_sz, style=piece_style)
        moved = board.piece_at(animation.to_sq)
        if moved:
            fx, fy = _sq_to_center_px(animation.from_sq, pos, sq_size=sq_sz, flipped=flipped)
            tx, ty = _sq_to_center_px(animation.to_sq, pos, sq_size=sq_sz, flipped=flipped)
            _draw_piece_at(surface, moved.symbol(),
                           fx + (tx - fx) * t, fy + (ty - fy) * t,
                           sq_size=sq_sz, style=piece_style)
        if animation.rook_to is not None:
            rook = board.piece_at(animation.rook_to)
            if rook:
                fx, fy = _sq_to_center_px(animation.rook_from, pos, sq_size=sq_sz, flipped=flipped)
                tx, ty = _sq_to_center_px(animation.rook_to, pos, sq_size=sq_sz, flipped=flipped)
                _draw_piece_at(surface, rook.symbol(),
                               fx + (tx - fx) * t, fy + (ty - fy) * t,
                               sq_size=sq_sz, style=piece_style)

# ----------------------------------------------------------------------
# TOURNAMENT WORKER
# ----------------------------------------------------------------------
class TournamentWorker(threading.Thread):
    def __init__(self, target_path, progress_queue, settings=None, rng=None,
                 skipped_indices=None, eval_cache=None):
        super().__init__(daemon=True)
        self.target_path = target_path
        self.queue = progress_queue
        self.settings = settings or {}
        self._rng = rng
        self.board = chess.Board()
        self.running = True
        self._schedule_lock = threading.Lock()
        self.skipped_opponent_indices = set(skipped_indices or ())
        self.schedule_entries = [
            {
                "index":  idx,
                "path":   opp_path,
                "name":   self._default_opp_label(opp_path),
                "rating": opp_rating,
                "status": "skipped" if idx in self.skipped_opponent_indices else "pending",
                "w":      0,
                "d":      0,
                "l":      0,
            }
            for idx, (opp_path, opp_rating) in enumerate(OPPONENTS)
        ]
        active_count = sum(1 for e in self.schedule_entries if e["status"] != "skipped")
        self.total_games = GAMES_PER_OPPONENT * active_count
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
        self.current_opponent_time_multiplier = 1.0
        self.current_opening_name = ""
        self._current_game_token = None
        self.high_elo_extended = False
        self.extension_start_index = None
        self.opponent_reloaded = False
        self.sound_events = deque(maxlen=512)

        # Decorative 30-second chess clocks (flag = loss on time)
        self.chess_clock_initial = float(self.settings.get("chess_clock", 30.0))
        self.white_clock = self.chess_clock_initial
        self.black_clock = self.chess_clock_initial
        self.clock_active_color = None
        self.clock_turn_started = None

        # Game replay records, move-quality Elo, and optional Engine Data tracking
        self.eval_cache = eval_cache if eval_cache is not None else {}
        self.game_records = []
        self.move_quality_summary = None
        self.last_game_move_quality = None
        self.engine_data_tracking = bool(self.settings.get("engine_data_tracking", False))
        _ef = globals().get("ef")
        self.resource_tracker = _ef.EngineResourceTracker() if _ef is not None else None
        self.resource_summary = None

    @staticmethod
    def _default_opp_label(path):
        if not path:
            return "Opponent"
        base = os.path.splitext(os.path.basename(path))[0]
        parent = os.path.basename(os.path.dirname(path))
        if parent.lower() in ("windows", "64", "gcc", "amd 64", "stockfish"):
            grand = os.path.basename(os.path.dirname(os.path.dirname(path)))
            if grand and grand.lower() not in ("chess", "engines", "stockfish"):
                return grand
        if parent and parent.lower().startswith("stockfish "):
            return parent
        return base

    def toggle_skip_opponent(self, opp_idx):
        with self._schedule_lock:
            for entry in self.schedule_entries:
                if entry["index"] == opp_idx:
                    if entry["status"] == "pending":
                        entry["status"] = "skipped"
                        self.skipped_opponent_indices.add(opp_idx)
                        self.total_games = max(
                            self.games_played, self.total_games - GAMES_PER_OPPONENT
                        )
                        return True
                    if entry["status"] == "skipped":
                        entry["status"] = "pending"
                        self.skipped_opponent_indices.discard(opp_idx)
                        self.total_games += GAMES_PER_OPPONENT
                        return False
                    return None
        return None

    def is_opponent_skipped(self, opp_idx):
        with self._schedule_lock:
            return opp_idx in self.skipped_opponent_indices

    def _update_schedule_entry(self, opp_idx, **updates):
        with self._schedule_lock:
            for entry in self.schedule_entries:
                if entry["index"] == opp_idx:
                    entry.update(updates)
                    return

    def get_schedule_snapshot(self):
        with self._schedule_lock:
            return [dict(e) for e in self.schedule_entries]

    def get_live_clocks(self):
        w_left = getattr(self, "white_clock", 30.0)
        b_left = getattr(self, "black_clock", 30.0)
        active = getattr(self, "clock_active_color", None)
        started = getattr(self, "clock_turn_started", None)
        if active is not None and started is not None:
            dt = max(0.0, time.monotonic() - started)
            if active is True:
                w_left = max(0.0, w_left - dt)
            elif active is False:
                b_left = max(0.0, b_left - dt)
        return (w_left, b_left)

    @staticmethod
    def _classify_move_sound(is_check=False, is_promotion=False, is_castling=False):
        if is_check:
            return "move-check"
        if is_promotion:
            return "promote"
        if is_castling:
            return "castle"
        return "move-self"

    def _emit_sound(self, sound_key):
        events = getattr(self, "sound_events", None)
        if events is not None:
            events.append(sound_key)

    def stop(self):
        self.running = False
        for eng in (self.target_engine, self.opponent_engine, self.adjudicator_engine):
            if eng is None:
                continue
            protocol = getattr(eng, "protocol", None)
            loop = getattr(protocol, "loop", None)
            if loop is not None and protocol is not None:
                def _abort_engine(proto=protocol):
                    try:
                        proto.send_line("stop")
                    except Exception:
                        pass
                    transport = getattr(proto, "transport", None)
                    if transport is not None:
                        try:
                            transport.kill()
                        except Exception:
                            pass
                try:
                    loop.call_soon_threadsafe(_abort_engine)
                    continue
                except Exception:
                    pass
            try:
                eng.close()
            except Exception:
                pass

    def _launch_engine(self, path, is_adjudicator=False):
        eng = chess.engine.SimpleEngine.popen(CompatibleUciProtocol, path)
        cfg = {}
        eff_settings = {"threads": 1, "hash": 16} if is_adjudicator else self.settings
        try:
            cfg = build_engine_config(eng, is_adjudicator=is_adjudicator,
                                      path=path, settings=eff_settings)
            apply_engine_config(eng, cfg)
            # configure() only sends UCI commands. Wait for readyok so an
            # allocation failure is reported here, not as ten failed moves.
            eng.ping()
        except Exception as exc:
            details = _engine_failure_details(exc, eng)
            self._kill_engine(eng)
            raise chess.engine.EngineError(
                f"Engine failed during configuration/readiness: {path}\n"
                f"Applied options: {cfg!r}\n{details}") from exc
        if not is_adjudicator:
            requested_hash = self.settings.get("hash")
            if requested_hash is not None and cfg.get("Hash", requested_hash) < requested_hash:
                self.queue.put(("status", f"{get_engine_name(eng)}: using Hash={cfg['Hash']} MB "
                                f"instead of {requested_hash} MB (compatibility/option limits)"))
        return eng

    def _kill_engine(self, eng):
        if eng is None:
            return
        old_timeout = eng.timeout
        try:
            # SimpleEngine's normal 10s timeout is useful for startup/search,
            # but not for an old engine stuck joining its threads on exit.
            eng.timeout = ENGINE_QUIT_TIMEOUT
            eng.quit()
        except Exception:
            pass
        finally:
            eng.timeout = old_timeout
            try:
                # Kills the subprocess if graceful quit timed out; also closes
                # python-chess's transport and background event loop.
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

    def _apply_opponent_metadata(self, engine, path):
        mult = getattr(self, "current_opponent_time_multiplier", 1.0)
        base_name = get_engine_name(engine, os.path.basename(path) if path else self.opponent_name)
        if mult > 1.0:
            mult_label = format_time_multiplier(mult)
            self.opponent_name = f"{base_name} ({mult_label} time)"
        elif base_name:
            self.opponent_name = base_name
        cfg_str = format_config(
            build_engine_config(engine, path=path, settings=self.settings))
        if mult > 1.0:
            opp_time = self.settings.get("time", TIME_LIMIT) * mult
            self.opponent_config_str = f"{cfg_str}, Move={opp_time:.2f}s ({format_time_multiplier(mult)})"
        else:
            self.opponent_config_str = cfg_str

    def _reload_opponent(self):
        self.queue.put(("status", "Reloading opponent engine…"))
        self._kill_engine(self.opponent_engine)
        self.opponent_engine = self._launch_engine(self.current_opponent_path,
                                                    is_adjudicator=False)
        try:
            self._apply_opponent_metadata(self.opponent_engine, self.current_opponent_path)
        except Exception:
            pass

    def _reload_adjudicator(self):
        self.queue.put(("status", "Reloading adjudicator…"))
        self._kill_engine(self.adjudicator_engine)
        self.adjudicator_engine = self._launch_engine(ADJUDICATOR_PATH,
                                                       is_adjudicator=True)

    def _report_error(self, summary, exc, role="target", failures=None, board=None):
        board = self.board if board is None else board
        engine = {"target": self.target_engine, "opponent": self.opponent_engine,
                  "adjudicator": self.adjudicator_engine}.get(role)
        fallback = {"target": self.target_name, "opponent": self.opponent_name,
                    "adjudicator": "Adjudicator"}.get(role, role.capitalize())
        name = get_engine_name(engine, fallback)
        extra_meta = []
        mult = getattr(self, "current_opponent_time_multiplier", 1.0)
        if mult != 1.0:
            extra_meta.append(f"Opponent time odds: {mult:g}x")
        opening_name = getattr(self, "current_opening_name", "")
        if opening_name:
            extra_meta.append(f"Opening: {opening_name}")
        report = "\n".join([
            "Eloify engine error report",
            summary,
            "Last error: " + _exception_message(exc),
            "",
            "Time: " + datetime.now().astimezone().isoformat(),
            f"Engine role: {role}",
            f"Engine name: {name}",
            f"Target executable: {self.target_path}",
            f"Opponent executable: {self.current_opponent_path}",
            f"Adjudicator executable: {ADJUDICATOR_PATH}",
            f"Settings: {self.settings!r}",
            *extra_meta,
            f"Completed games: {self.games_played}",
            f"Position (FEN): {board.fen()}",
            "Moves (UCI): " + " ".join(move.uci() for move in board.move_stack),
            "",
            "Failure history / tracebacks:",
            "\n".join(failures) if failures else _engine_failure_details(exc, engine),
        ])
        log_path, log_error = _save_error_log(report)
        if log_path:
            report = f"Log file: {log_path}\n\n" + report
        else:
            report = "Log file could not be saved:\n" + log_error + "\n\n" + report
        self.queue.put(("error", {"summary": summary, "report": report,
                                  "log_path": log_path, "log_error": log_error}))

    def _safe_play(self, board, role):
        consecutive_target_fails = 0
        failures = []
        base_time = self.settings.get("time", TIME_LIMIT)
        if role == "opponent":
            time_limit = base_time * getattr(self, "current_opponent_time_multiplier", 1.0)
        else:
            time_limit = base_time
        while True:
            if not self.running:
                raise TournamentAborted()
            engine = self.target_engine if role == "target" else self.opponent_engine
            try:
                game_token = getattr(self, "_current_game_token", None)
                if game_token is not None:
                    result = engine.play(board, chess.engine.Limit(time=time_limit),
                                         game=game_token)
                else:
                    result = engine.play(board, chess.engine.Limit(time=time_limit))
                if result is None or result.move is None:
                    raise ValueError("Engine returned no move")
                if result.move not in board.legal_moves:
                    raise ValueError(f"Engine returned illegal move: {result.move}")
                return result
            except Exception as e:
                if not self.running:
                    raise TournamentAborted() from e
                failures.append(f"Attempt {len(failures) + 1}: {_exception_message(e)}\n"
                                + _engine_failure_details(e, engine))
                self.queue.put(("status", f"{role.capitalize()} engine error: {_exception_message(e)}"))
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
                    if consecutive_target_fails >= MAX_MOVE_RETRIES:
                        self._report_error(
                            f"Target failed {consecutive_target_fails} times consecutively — forfeiting game",
                            e, role, failures, board)
                        self.running = False
                        raise TournamentAborted() from e
                    try:
                        self._reload_target()
                        self.queue.put(("status", "Target reloaded — retrying"))
                    except Exception as reload_err:
                        failures.append("Target reload failed:\n"
                                        + _engine_failure_details(reload_err, self.target_engine))
                        self._report_error("Could not reload target", reload_err,
                                           role, failures, board)
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
                if not self.running:
                    return None
                self.queue.put(("status", f"Adjudicator error: {e}"))
                try:
                    self._reload_adjudicator()
                except Exception as reload_err:
                    self.queue.put(("status", f"Adjudicator reload failed: {reload_err}"))
                    self.adjudicator_engine = None
                    return None
        return None

    def _finalize_game_record(self, result_code, pgn_result, termination_label,
                              target_is_white, initial_fen, opening_name, ply_records):
        _ef = globals().get("ef")
        eval_cache = getattr(self, "eval_cache", None) or {}
        if eval_cache:
            for ply in ply_records:
                fb = ply.get("fen_before")
                fa = ply.get("fen_after")
                if fb in eval_cache:
                    ply["eval_before_cp"] = eval_cache[fb][0]
                if fa in eval_cache:
                    ply["eval_after_cp"] = eval_cache[fa][0]
                    ply["mate_after"] = eval_cache[fa][1]

        mq = None
        if _ef is not None and self.settings.get("move_quality_elo", True):
            try:
                mq = _ef.compute_game_move_quality_elo(ply_records, target_is_white)
            except Exception:
                mq = None
        self.last_game_move_quality = mq

        res_stats = None
        tracker = getattr(self, "resource_tracker", None)
        if getattr(self, "engine_data_tracking", False) and tracker is not None:
            try:
                res_stats = tracker.finish_game()
                self.resource_summary = tracker.summary()
            except Exception:
                res_stats = None

        records = getattr(self, "game_records", None)
        if records is not None:
            rec = {
                "game_number":     len(records) + 1,
                "opponent_index":  getattr(self, "current_opponent_index", 0),
                "opponent_name":   getattr(self, "opponent_name", "Opponent"),
                "opponent_rating": getattr(self, "opponent_rating", 0),
                "target_name":     getattr(self, "target_name", "Target"),
                "target_is_white": bool(target_is_white),
                "result":          result_code,
                "pgn_result":      pgn_result,
                "termination":     termination_label,
                "opening_name":    opening_name or "",
                "initial_fen":     initial_fen,
                "plies":           ply_records,
                "move_quality":    mq,
                "resource_stats":  res_stats,
            }
            records.append(rec)
            if _ef is not None and self.settings.get("move_quality_elo", True):
                try:
                    self.move_quality_summary = _ef.aggregate_move_quality_elo(records)
                except Exception:
                    pass

    def _play_opponent_match(self, opp_path, opp_rating, opp_idx, label,
                             time_multiplier=1.0, openings_for_games=None):
        if hasattr(self, "is_opponent_skipped") and self.is_opponent_skipped(opp_idx):
            if hasattr(self, "_update_schedule_entry"):
                self._update_schedule_entry(opp_idx, status="skipped")
            self.queue.put(("status", f"Skipped {label} ({opp_rating} Elo)"))
            return False, False

        self.current_opponent_path = opp_path
        self.current_opponent_time_multiplier = float(time_multiplier)
        self.opponent_reloaded = False
        try:
            self.opponent_engine = self._launch_engine(opp_path, is_adjudicator=False)
        except Exception as launch_err:
            if hasattr(self, "_update_schedule_entry"):
                self._update_schedule_entry(opp_idx, status="unavailable")
            self.total_games = max(self.games_played, self.total_games - GAMES_PER_OPPONENT)
            self.queue.put(("status", f"{label} launch failed, skipping: {launch_err}"))
            self.current_opponent_time_multiplier = 1.0
            return False, False

        is_maia = is_maia_engine(self.opponent_engine, opp_path)
        self.opponent_rating = opp_rating
        self.current_opponent_index = opp_idx
        self._apply_opponent_metadata(self.opponent_engine, opp_path)
        if hasattr(self, "_update_schedule_entry"):
            self._update_schedule_entry(
                opp_idx, name=self.opponent_name, status="playing"
            )
        if is_maia:
            self.queue.put(("status", f"Opponent: {self.opponent_name} (Maia — NPS=1 applied)"))

        per_game = []
        try:
            for game_idx in range(GAMES_PER_OPPONENT):
                if not self.running:
                    break
                target_is_white = (game_idx % 2 == 0)
                opening = (openings_for_games[game_idx]
                           if openings_for_games and game_idx < len(openings_for_games)
                           else None)
                try:
                    result = self.play_game(target_is_white, opening=opening)
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
                if hasattr(self, "_update_schedule_entry"):
                    self._update_schedule_entry(
                        opp_idx,
                        w=per_game.count("W"),
                        d=per_game.count("D"),
                        l=per_game.count("L"),
                    )
        finally:
            self._kill_engine(self.opponent_engine)
            self.opponent_engine = None
            self.current_opponent_time_multiplier = 1.0
            self.current_opening_name = ""

        w = per_game.count("W")
        d = per_game.count("D")
        l = per_game.count("L")
        if hasattr(self, "_update_schedule_entry"):
            self._update_schedule_entry(
                opp_idx,
                name=self.opponent_name,
                status="done" if (w + d + l > 0) else "unavailable",
                w=w, d=d, l=l,
            )
        if w + d + l > 0:
            self.per_opponent_results.append(
                (self.opponent_name, opp_rating, w, d, l))
            return True, (not is_maia)
        return False, False

    def run(self):
        try:
            self.queue.put(("status", "Launching target engine…"))
            try:
                self.target_engine = self._launch_engine(self.target_path, is_adjudicator=False)
            except Exception as e:
                self._report_error("Could not launch target engine", e)
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

            if getattr(self, "engine_data_tracking", False) and getattr(self, "resource_tracker", None):
                try:
                    self.resource_tracker.sample(engine=self.target_engine)
                    self.resource_summary = self.resource_tracker.summary()
                except Exception:
                    pass

            self.queue.put(("status", "Launching adjudicator…"))
            try:
                self.adjudicator_engine = self._launch_engine(ADJUDICATOR_PATH,
                                                              is_adjudicator=True)
            except Exception as e:
                self.adjudicator_engine = None
                self.queue.put(("status", f"Adjudicator unavailable (continuing without): {e}"))

            working_opponents = []
            for opp_idx, (opp_path, opp_rating) in enumerate(OPPONENTS):
                if not self.running:
                    break
                if hasattr(self, "is_opponent_skipped") and self.is_opponent_skipped(opp_idx):
                    if hasattr(self, "_update_schedule_entry"):
                        self._update_schedule_entry(opp_idx, status="skipped")
                    continue
                self.queue.put(("status", f"Launching opponent {opp_idx + 1}…"))
                played, can_scale = self._play_opponent_match(
                    opp_path, opp_rating, opp_idx, f"Opponent {opp_idx + 1}")
                if played and can_scale:
                    working_opponents.append((opp_path, opp_rating))

            if (self.running
                    and self.games_played > 0
                    and should_run_high_elo_extension(self.per_opponent_results)):
                adjudicator_usable = (
                    self.adjudicator_engine is not None
                    and not is_maia_engine(self.adjudicator_engine, ADJUDICATOR_PATH)
                )
                anchor = select_high_elo_anchor(
                    working_opponents,
                    adjudicator_path=ADJUDICATOR_PATH,
                    adjudicator_available=adjudicator_usable,
                    configured_opponents=OPPONENTS,
                )
                if anchor is not None:
                    ext_tiers = build_high_elo_tiers(anchor[0], anchor[1])
                    if ext_tiers:
                        self.high_elo_extended = True
                        self.extension_start_index = len(self.per_opponent_results)
                        if hasattr(self, "_schedule_lock"):
                            with self._schedule_lock:
                                base_label = self._default_opp_label(anchor[0])
                                for tier_idx, (t_path, t_rating, t_mult) in enumerate(ext_tiers):
                                    ext_idx = len(OPPONENTS) + tier_idx
                                    self.schedule_entries.append({
                                        "index":  ext_idx,
                                        "path":   t_path,
                                        "name":   f"{base_label} ({format_time_multiplier(t_mult)})",
                                        "rating": t_rating,
                                        "status": "skipped" if ext_idx in self.skipped_opponent_indices else "pending",
                                        "w":      0,
                                        "d":      0,
                                        "l":      0,
                                    })
                        active_ext = sum(
                            1 for tier_idx in range(len(ext_tiers))
                            if not (hasattr(self, "is_opponent_skipped")
                                    and self.is_opponent_skipped(len(OPPONENTS) + tier_idx))
                        )
                        self.total_games = self.games_played + GAMES_PER_OPPONENT * active_ext
                        ext_openings = select_extension_openings(
                            len(ext_tiers),
                            games_per_opponent=GAMES_PER_OPPONENT,
                            rng=self._rng,
                        )
                        self.queue.put((
                            "status",
                            f"Top engine detected — extending test beyond 3600 Elo "
                            f"(up to {ext_tiers[-1][1]} Elo)…",
                        ))
                        for tier_idx, (t_path, t_rating, t_mult) in enumerate(ext_tiers):
                            if not self.running:
                                break
                            ext_idx = len(OPPONENTS) + tier_idx
                            if hasattr(self, "is_opponent_skipped") and self.is_opponent_skipped(ext_idx):
                                if hasattr(self, "_update_schedule_entry"):
                                    self._update_schedule_entry(ext_idx, status="skipped")
                                continue
                            mult_label = format_time_multiplier(t_mult)
                            self.queue.put((
                                "status",
                                f"Extended tier {tier_idx + 1}/{len(ext_tiers)}: "
                                f"{t_rating} Elo ({mult_label} move time)…",
                            ))
                            self._play_opponent_match(
                                t_path,
                                t_rating,
                                ext_idx,
                                f"Extended tier {tier_idx + 1}",
                                time_multiplier=t_mult,
                                openings_for_games=ext_openings[tier_idx],
                            )

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
            self._report_error("Unexpected tournament error", e)
            self._kill_engine(self.target_engine)
            self._kill_engine(self.opponent_engine)
            self._kill_engine(self.adjudicator_engine)

    def play_game(self, target_is_white, opening=None):
        self.board.reset()
        self._current_game_token = object()
        self.current_move_number = 0
        self.last_move_san = ""
        self.last_move_uci = ""
        self.recent_moves = []
        self.current_opening_name = ""
        init_clock = float(getattr(self, "chess_clock_initial", 30.0))
        self.white_clock = init_clock
        self.black_clock = init_clock
        self.clock_active_color = None
        self.clock_turn_started = None

        tracker = getattr(self, "resource_tracker", None)
        if getattr(self, "engine_data_tracking", False) and tracker is not None:
            try:
                tracker.start_game()
            except Exception:
                pass

        if opening:
            opening_name, opening_moves = opening
            self.current_opening_name = opening_name
            for uci_move in opening_moves:
                move = chess.Move.from_uci(uci_move)
                if move not in self.board.legal_moves:
                    break
                try:
                    san = self.board.san(move)
                except Exception:
                    san = uci_move
                self.board.push(move)
                self.last_move_san = san
                self.last_move_uci = uci_move
                self.recent_moves.append(san)
            if len(self.recent_moves) > 12:
                self.recent_moves = self.recent_moves[-12:]
        initial_fen = self.board.fen()
        self.current_fen_shared = initial_fen
        self.target_is_white = target_is_white
        self.last_game_was_checkmate = False
        if not self.running:
            raise TournamentAborted()
        self._emit_sound("game-start")

        ply_records = []
        prev_search_white_cp = None

        # Play until real chess termination (checkmate, stalemate, insufficient
        # material, 50-move rule, threefold repetition) or 30s clock flag!
        while not (
            self.board.is_game_over()
            or self.board.is_fifty_moves()
            or self.board.is_repetition(3)
        ):
            if not self.running:
                raise TournamentAborted()
            mover_is_white = (self.board.turn == chess.WHITE)
            role = "target" if (mover_is_white == target_is_white) else "opponent"
            rem_before = self.white_clock if mover_is_white else self.black_clock
            if rem_before <= 0.0:
                if mover_is_white == target_is_white:
                    self.last_game_result = "Opponent wins (on time)"
                    res_code = "L"
                else:
                    self.last_game_result = "Target wins (on time)"
                    res_code = "W"
                pgn_res = "0-1" if mover_is_white else "1-0"
                if hasattr(self, "_finalize_game_record"):
                    self._finalize_game_record(
                        res_code, pgn_res, "TIME_FORFEIT",
                        target_is_white, initial_fen, self.current_opening_name, ply_records,
                    )
                self._emit_sound("game-end")
                return res_code

            fen_before = self.board.fen()
            timed_out = [False]
            active_eng = self.target_engine if role == "target" else self.opponent_engine

            def _on_clock_expired(eng=active_eng):
                timed_out[0] = True
                proto = getattr(eng, "protocol", None)
                loop = getattr(proto, "loop", None)
                if loop is not None and proto is not None:
                    try:
                        loop.call_soon_threadsafe(proto.send_line, "stop")
                    except Exception:
                        pass

            flag_timer = threading.Timer(max(0.001, rem_before), _on_clock_expired)
            flag_timer.daemon = True
            self.clock_active_color = mover_is_white
            t0 = time.monotonic()
            self.clock_turn_started = t0
            flag_timer.start()
            try:
                result = self._safe_play(self.board, role)
            except Exception:
                flag_timer.cancel()
                self.clock_active_color = None
                self.clock_turn_started = None
                if timed_out[0] and self.running:
                    result = None
                else:
                    raise
            else:
                flag_timer.cancel()
                self.clock_active_color = None
                self.clock_turn_started = None

            dt = max(0.0, time.monotonic() - t0)
            if mover_is_white:
                self.white_clock = max(0.0, self.white_clock - dt)
                rem_after = self.white_clock
            else:
                self.black_clock = max(0.0, self.black_clock - dt)
                rem_after = self.black_clock

            if getattr(self, "engine_data_tracking", False) and tracker is not None and role == "target":
                try:
                    t_proto = getattr(self.target_engine, "protocol", None)
                    nps = getattr(t_proto, "latest_nps", 0)
                    self.resource_summary = tracker.sample(
                        engine=self.target_engine, latest_nps=nps
                    )
                except Exception:
                    pass

            if timed_out[0] or rem_after <= 0.0 or result is None or getattr(result, "move", None) is None:
                if mover_is_white:
                    self.white_clock = 0.0
                else:
                    self.black_clock = 0.0
                if mover_is_white == target_is_white:
                    self.last_game_result = "Opponent wins (on time)"
                    res_code = "L"
                else:
                    self.last_game_result = "Target wins (on time)"
                    res_code = "W"
                pgn_res = "0-1" if mover_is_white else "1-0"
                if hasattr(self, "_finalize_game_record"):
                    self._finalize_game_record(
                        res_code, pgn_res, "TIME_FORFEIT",
                        target_is_white, initial_fen, self.current_opening_name, ply_records,
                    )
                self._emit_sound("game-end")
                return res_code

            # Capture engine's own search score if emitted via UCI info
            used_eng = self.target_engine if role == "target" else self.opponent_engine
            proto = getattr(used_eng, "protocol", None)
            raw_cp = getattr(proto, "latest_score_cp", None)
            search_white_cp = None
            if raw_cp is not None:
                search_white_cp = int(raw_cp) if mover_is_white else -int(raw_cp)
                if ply_records and ply_records[-1].get("eval_after_cp") is None:
                    ply_records[-1]["eval_after_cp"] = search_white_cp

            is_castling = self.board.is_castling(result.move)
            is_promotion = result.move.promotion is not None
            try:
                san = self.board.san(result.move)
            except Exception:
                san = result.move.uci()
            uci_str = result.move.uci()
            self.board.push(result.move)
            fen_after = self.board.fen()
            is_check = self.board.is_check()
            self._emit_sound(self._classify_move_sound(
                is_check=is_check,
                is_promotion=is_promotion,
                is_castling=is_castling,
            ))
            self.current_move_number += 1
            self.last_move_san = san
            self.last_move_uci = uci_str
            self.total_move_counter += 1
            self.recent_moves.append(san)
            if len(self.recent_moves) > 12:
                self.recent_moves = self.recent_moves[-12:]
            self.current_fen_shared = fen_after

            ply_records.append({
                "ply":            self.current_move_number,
                "uci":            uci_str,
                "san":            san,
                "mover_is_white": mover_is_white,
                "fen_before":     fen_before,
                "fen_after":      fen_after,
                "move_time":      round(dt, 4),
                "white_left":     round(self.white_clock, 3),
                "black_left":     round(self.black_clock, 3),
                "eval_before_cp": search_white_cp if search_white_cp is not None else prev_search_white_cp,
                "eval_after_cp":  None,
                "mate_after":     None,
            })
            prev_search_white_cp = search_white_cp

        outcome = self.board.outcome()
        if outcome is None:
            if self.board.is_fifty_moves():
                outcome = chess.Outcome(chess.Termination.FIFTY_MOVES, None)
            elif self.board.is_repetition(3):
                outcome = chess.Outcome(chess.Termination.THREEFOLD_REPETITION, None)
        try:
            self.last_game_was_checkmate = (
                outcome is not None
                and outcome.termination is not None
                and outcome.termination == chess.Termination.CHECKMATE)
        except Exception:
            self.last_game_was_checkmate = False

        term_name = outcome.termination.name if (outcome and outcome.termination) else "DRAW"
        if outcome is None or outcome.winner is None:
            self.last_game_result = f"Draw ({term_name})"
            if hasattr(self, "_finalize_game_record"):
                self._finalize_game_record(
                    "D", "1/2-1/2", term_name,
                    target_is_white, initial_fen, self.current_opening_name, ply_records,
                )
            self._emit_sound("game-end")
            return "D"
        if outcome.winner == chess.WHITE:
            res_code = "W" if target_is_white else "L"
            self.last_game_result = (
                "Target wins (1-0)" if target_is_white else "Opponent wins (1-0)"
            )
            if hasattr(self, "_finalize_game_record"):
                self._finalize_game_record(
                    res_code, "1-0", term_name,
                    target_is_white, initial_fen, self.current_opening_name, ply_records,
                )
            self._emit_sound("game-end")
            return res_code
        res_code = "L" if target_is_white else "W"
        self.last_game_result = (
            "Opponent wins (0-1)" if target_is_white else "Target wins (0-1)"
        )
        if hasattr(self, "_finalize_game_record"):
            self._finalize_game_record(
                res_code, "0-1", term_name,
                target_is_white, initial_fen, self.current_opening_name, ply_records,
            )
        self._emit_sound("game-end")
        return res_code

# ----------------------------------------------------------------------
# MAIN APPLICATION
# ----------------------------------------------------------------------
class EloifyApp:
    def __init__(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        _init_font_family()

        try:
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(len(AUDIO_SOUND_FILES))
        except Exception:
            pass

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Eloify – Chess Engine Elo Tester")
        self.clock = pygame.time.Clock()

        self.drumroll_sound    = None
        self.celebration_sound = None
        self.sounds            = {}
        self.sound_channels    = {}
        self.castle_sound      = None
        self.game_start_sound  = None
        self.game_end_sound    = None
        self.move_sound        = None
        self.check_sound       = None
        self.promote_sound     = None

        if pygame.mixer.get_init():
            try:
                self.drumroll_sound    = _generate_drumroll()
                self.celebration_sound = _generate_celebration()
            except Exception:
                pass
            try:
                self.sounds            = _load_game_sounds()
                self.castle_sound      = self.sounds.get("castle")
                self.game_start_sound  = self.sounds.get("game-start")
                self.game_end_sound    = self.sounds.get("game-end")
                self.move_sound        = self.sounds.get("move-self")
                self.check_sound       = self.sounds.get("move-check")
                self.promote_sound     = self.sounds.get("promote")
                for idx, key in enumerate((
                    "game-start",
                    "game-end",
                    "move-self",
                    "move-check",
                    "castle",
                    "promote",
                )):
                    self.sound_channels[key] = pygame.mixer.Channel(idx)
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
        self.error_report = ""
        self.error_clipboard_status = ""
        self.error_scroll = 0
        self.results_scroll = 0
        self._error_lines = None
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
        self.browse_show_hidden = False
        self.browse_hidden_count = 0
        self.browse_error = ""
        self.browse_focus = "text"      # "text" or "list"
        self.browse_path_field = TextField("")
        self.browse_drag_active = False
        self._keys_down = set()
        self._last_browse_click_time = 0.0
        self._last_browse_click_idx = -1

        # ---- Feature settings: board, piece style, theme, audio, tracking ----
        self.cfg_auto_rotate_board    = False
        self.cfg_hide_coords          = False
        self.cfg_engine_data_tracking = False
        self.cfg_move_quality_elo     = True

        self.theme_mode = "dark"
        self.accent_key = "emerald"
        self.board_skin = "classic_wood"
        self.custom_light_sq = [238, 216, 183]
        self.custom_dark_sq  = [171, 122, 89]
        self.piece_style     = "classic_2tone"

        self.audio_muted  = False
        self.audio_volume = 1.0
        self.dragging_audio_volume = False
        self.dragging_rgb_slider   = None
        self.settings_tab          = 0  # 0=Engine & Rules, 1=Board & Pieces, 2=Theme & Accents

        # ---- Engine playlist ("Next in line") ----
        self.engine_playlist       = []
        self.playlist_scroll       = 0
        self.browse_mode           = "primary"
        self.active_playlist_paths = []
        self.playlist_current_idx  = 0
        self.playlist_results      = []
        self.selected_result_idx   = 0

        # ---- Live & post-test UI state ----
        self.running_opp_scroll    = 0
        self.running_opp_autoscroll = True
        self.confirm_back_to_menu  = False
        self.done_scroll_y         = 0
        self.done_max_scroll       = 0
        self._done_game_hitboxes   = []
        self._done_playlist_hitboxes = []
        self._running_skip_hitboxes = []
        self._playlist_row_hitboxes = []

        # ---- Live Eval Worker & Replay Viewer state ----
        self.shared_eval_cache   = {}
        self.live_eval_worker    = None
        self.replay_eval_worker  = None
        self._displayed_eval_frac = 0.5
        self.replay_game         = None
        self.replay_ply          = 0
        self.replay_flipped      = None
        self.replay_moves_scroll = 0
        self._replay_move_hitboxes = []

        # ---- Main menu animation state ----
        self._menu_time = 0.0
        self._menu_bg_gradient = self._make_menu_bg_gradient()
        self._menu_title_glow = None
        self._menu_particles = []
        self._init_menu_particles()

        # Buttons (main menu)
        self.browse_rect      = pygame.Rect(50, 672, 340, 62)
        self.customize_rect   = pygame.Rect(410, 672, 340, 62)
        self.start_rect       = pygame.Rect(770, 672, 420, 62)
        self.edit_system_rect = pygame.Rect(422, 184, 62, 26)
        self.quick_theme_rect = pygame.Rect(WINDOW_WIDTH - 196, 44, 146, 34)
        self.playlist_add_rect   = pygame.Rect(988, 182, 108, 28)
        self.playlist_clear_rect = pygame.Rect(1104, 182, 68, 28)

        # Settings dialog buttons
        sp = self._get_settings_panel_rect()
        self.settings_reset_rect  = pygame.Rect(sp.x + 28, sp.bottom - 58, 160, 42)
        self.settings_cancel_rect = pygame.Rect(sp.right - 258, sp.bottom - 58, 110, 42)
        self.settings_save_rect   = pygame.Rect(sp.right - 136, sp.bottom - 58, 110, 42)

        # Live / Done top-bar controls
        self.running_back_rect = pygame.Rect(20, 18, 112, 34)
        self.running_mute_rect = pygame.Rect(WINDOW_WIDTH - 246, 18, 76, 32)
        self.running_vol_rect  = pygame.Rect(WINDOW_WIDTH - 158, 29, 134, 10)
        self.done_back_rect    = pygame.Rect(24, 12, 132, 34)
        self.replay_back_rect  = pygame.Rect(24, 14, 152, 34)
        self.replay_flip_rect  = pygame.Rect(188, 14, 118, 34)

        self.mouse_pos = (0, 0)
        self._sync_board_visuals()
        self._apply_audio_volume()

    # ------------------------------------------------------------------
    # THEME, BOARD VISUALS, AND AUDIO HELPERS
    # ------------------------------------------------------------------
    def _current_palette(self):
        return ef.get_theme_palette(
            getattr(self, "theme_mode", "dark"),
            getattr(self, "accent_key", "emerald"),
        )

    def _apply_theme(self, mode=None, accent_key=None):
        global BACKGROUND, PANEL, PANEL_HOVER, BORDER, TEXT_COLOR, DIM_TEXT
        global ACCENT, GOLD, ERROR_COLOR, WIN_COLOR, LOSS_COLOR, DRAW_COLOR
        global SELECTION_BG, FIELD_BG, FIELD_BORDER, LIST_BG, LIST_ROW_HOVER, LIST_ROW_SEL
        if mode is not None:
            self.theme_mode = mode
        if accent_key is not None:
            self.accent_key = accent_key
        pal = self._current_palette()
        BACKGROUND     = pal["BACKGROUND"]
        PANEL          = pal["PANEL"]
        PANEL_HOVER    = pal["PANEL_HOVER"]
        BORDER         = pal["BORDER"]
        TEXT_COLOR     = pal["TEXT_COLOR"]
        DIM_TEXT       = pal["DIM_TEXT"]
        ACCENT         = pal["ACCENT"]
        GOLD           = pal["GOLD"]
        ERROR_COLOR    = pal["ERROR_COLOR"]
        WIN_COLOR      = pal["WIN_COLOR"]
        LOSS_COLOR     = pal["LOSS_COLOR"]
        DRAW_COLOR     = pal["DRAW_COLOR"]
        SELECTION_BG   = pal["SELECTION_BG"]
        FIELD_BG       = pal["FIELD_BG"]
        FIELD_BORDER   = pal["FIELD_BORDER"]
        LIST_BG        = pal["LIST_BG"]
        LIST_ROW_HOVER = pal["LIST_ROW_HOVER"]
        LIST_ROW_SEL   = pal["LIST_ROW_SEL"]
        _TEXT_CACHE.clear()
        _PIECE_SURFACE_CACHE.clear()
        self._menu_bg_gradient = self._make_menu_bg_gradient()
        self._menu_title_glow = None
        self._elo_surface_cache = None

    def _sync_board_visuals(self):
        global _ACTIVE_BOARD_LIGHT, _ACTIVE_BOARD_DARK, _ACTIVE_PIECE_STYLE, _ACTIVE_SHOW_COORDS
        light_c, dark_c = ef.resolve_board_colors(
            getattr(self, "board_skin", "classic_wood"),
            getattr(self, "custom_light_sq", (238, 216, 183)),
            getattr(self, "custom_dark_sq", (171, 122, 89)),
        )
        _ACTIVE_BOARD_LIGHT = light_c
        _ACTIVE_BOARD_DARK  = dark_c
        _ACTIVE_PIECE_STYLE = getattr(self, "piece_style", "classic_2tone")
        _ACTIVE_SHOW_COORDS = not getattr(self, "cfg_hide_coords", False)

    def _apply_audio_volume(self):
        muted = getattr(self, "audio_muted", False)
        vol = 0.0 if muted else max(0.0, min(1.0, float(getattr(self, "audio_volume", 1.0))))
        for snd in (
            getattr(self, "drumroll_sound", None),
            getattr(self, "celebration_sound", None),
            *(getattr(self, "sounds", {}) or {}).values(),
        ):
            if snd is not None:
                try:
                    snd.set_volume(vol)
                except Exception:
                    pass
        for ch in (getattr(self, "sound_channels", {}) or {}).values():
            if ch is not None:
                try:
                    ch.set_volume(vol)
                except Exception:
                    pass

    def _draw_audio_controls(self, mute_rect, vol_rect):
        muted = getattr(self, "audio_muted", False)
        vol = max(0.0, min(1.0, float(getattr(self, "audio_volume", 1.0))))
        eff = 0.0 if muted else vol
        hov = mute_rect.collidepoint(self.mouse_pos)
        fill = PANEL_HOVER if hov else PANEL
        bdr = ERROR_COLOR if muted else (ACCENT if hov else BORDER)
        pygame.draw.rect(self.screen, fill, mute_rect, border_radius=7)
        pygame.draw.rect(self.screen, bdr, mute_rect, width=1, border_radius=7)
        lbl = "Muted" if muted else "Mute"
        col = ERROR_COLOR if muted else TEXT_COLOR
        s = _render_text(lbl, 13, col, True)
        self.screen.blit(s, s.get_rect(center=mute_rect.center))

        track_bg = (52, 58, 72) if getattr(self, "theme_mode", "dark") == "dark" else (204, 212, 226)
        pygame.draw.rect(self.screen, track_bg, vol_rect, border_radius=5)
        fill_w = int(round(vol_rect.w * eff))
        if fill_w > 0:
            pygame.draw.rect(
                self.screen,
                ACCENT,
                pygame.Rect(vol_rect.x, vol_rect.y, max(4, fill_w), vol_rect.h),
                border_radius=5,
            )
        knob_x = vol_rect.x + int(round(vol_rect.w * eff))
        pygame.draw.circle(self.screen, ACCENT if not muted else DIM_TEXT,
                           (knob_x, vol_rect.centery), 7)
        pygame.draw.circle(self.screen, BACKGROUND, (knob_x, vol_rect.centery), 3)
        pct_txt = f"{int(round(eff * 100))}%"
        draw_text(self.screen, pct_txt, (vol_rect.x + vol_rect.w // 2 - 14, vol_rect.bottom + 3),
                  11, DIM_TEXT)

    def _set_volume_from_mouse(self, vol_rect, mx):
        frac = max(0.0, min(1.0, (mx - vol_rect.x) / max(1, vol_rect.w)))
        self.audio_volume = round(frac, 3)
        if self.audio_volume > 0.0 and self.audio_muted:
            self.audio_muted = False
        self._apply_audio_volume()

    def _accept_browsed_engine(self, path):
        mode = getattr(self, "browse_mode", "primary")
        if mode == "playlist_add":
            self.engine_playlist.append(path)
            if not self.target_path:
                self.target_path = path
            self.status_text = (
                f"Added to playlist ({len(self.engine_playlist)} queued): "
                f"{os.path.basename(path)}"
            )
        else:
            self.target_path = path
            if not self.engine_playlist:
                self.engine_playlist = [path]
            else:
                self.engine_playlist[0] = path
            self.status_text = f"Selected: {os.path.basename(path)}"
        self.browse_mode = "primary"

    def _stop_aux_workers(self):
        for attr in ("live_eval_worker", "replay_eval_worker"):
            ew = getattr(self, attr, None)
            if ew is not None:
                try:
                    ew.stop()
                    ew.join(timeout=0.8)
                except Exception:
                    pass
                setattr(self, attr, None)

    # ------------------------------------------------------------------
    # MAIN MENU — decorative helpers
    # ------------------------------------------------------------------
    def _make_menu_bg_gradient(self):
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        is_light = sum(BACKGROUND) > 400
        for y in range(WINDOW_HEIGHT):
            t = y / max(1, WINDOW_HEIGHT - 1)
            if is_light:
                r = max(0, min(255, int(BACKGROUND[0] - 12 * t)))
                g = max(0, min(255, int(BACKGROUND[1] - 10 * t)))
                b = max(0, min(255, int(BACKGROUND[2] - 6 * t)))
            else:
                r = max(0, min(255, int(BACKGROUND[0] * (0.85 + 0.35 * t))))
                g = max(0, min(255, int(BACKGROUND[1] * (0.85 + 0.30 * t))))
                b = max(0, min(255, int(BACKGROUND[2] * (0.85 + 0.20 * t))))
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
        is_light = sum(BACKGROUND) > 400
        if not enabled:
            fill = (212, 218, 228) if is_light else (42, 46, 56)
            border = (188, 196, 210) if is_light else (60, 64, 76)
            text_color = (140, 148, 162) if is_light else (120, 125, 135)
        elif primary:
            pulse = 0.5 + 0.5 * math.sin(self._menu_time * 3.5)
            mix = 0.86 + 0.14 * pulse
            fill = tuple(max(0, min(255, int(c * mix))) for c in ACCENT)
            if hovered:
                fill = tuple(max(0, min(255, int(c * 1.08 + 8))) for c in fill)
            border = tuple(max(0, min(255, c + 35)) for c in ACCENT)
            lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
            text_color = (14, 20, 26) if lum > 145 else (248, 250, 252)
        elif hovered:
            fill, border, text_color = PANEL_HOVER, ACCENT, TEXT_COLOR
        else:
            fill, border, text_color = PANEL, BORDER, TEXT_COLOR
        shadow_col = (185, 192, 206) if is_light else (12, 14, 18)
        pygame.draw.rect(self.screen, shadow_col,
                         pygame.Rect(rect.x, rect.y + 3, rect.width, rect.height),
                         border_radius=12)
        if primary and enabled:
            glow_rect = rect.inflate(16, 16)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height),
                                       pygame.SRCALPHA)
            glow_alpha = 40 + int(30 * (0.5 + 0.5 * math.sin(self._menu_time * 3.5)))
            pygame.draw.rect(glow_surf, (*ACCENT, glow_alpha),
                             glow_surf.get_rect(), border_radius=18)
            self.screen.blit(glow_surf, glow_rect)
        pygame.draw.rect(self.screen, fill, rect, border_radius=12)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=12)
        surf = _render_text(label, 20, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_edit_button(self, rect, label="Edit"):
        hovered = rect.collidepoint(self.mouse_pos)
        if hovered:
            fill = PANEL_HOVER
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = PANEL
            border = BORDER
            text_color = DIM_TEXT
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
        surf = _render_text(label, 13, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def _draw_stat_panel(self, rect, title, rows, accent=None):
        accent = accent or ACCENT
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=12)
        pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=12)
        draw_text(self.screen, title, (rect.x + 20, rect.y + 14), 14, accent, bold=True)
        pygame.draw.line(self.screen, BORDER,
                         (rect.x + 20, rect.y + 38),
                         (rect.right - 20, rect.y + 38), 1)
        for i, (label, value, color) in enumerate(rows):
            ry = rect.y + 50 + i * 24
            draw_text(self.screen, label, (rect.x + 20, ry), 14, DIM_TEXT)
            vsurf = _render_text(str(value), 14, color or TEXT_COLOR, True)
            self.screen.blit(vsurf, (rect.right - 20 - vsurf.get_width(), ry))

    # ------------------------------------------------------------------
    # SETTINGS & CUSTOMIZATION DIALOG (3 TABS)
    # ------------------------------------------------------------------
    def _get_settings_panel_rect(self):
        return pygame.Rect((WINDOW_WIDTH - 960) // 2, (WINDOW_HEIGHT - 650) // 2, 960, 650)

    def _get_settings_tab_rects(self):
        panel = self._get_settings_panel_rect()
        labels = ("Engine & Rules", "Board & Pieces", "Theme & Accents")
        rects = []
        tx = panel.x + 30
        for lbl in labels:
            rects.append((pygame.Rect(tx, panel.y + 58, 190, 34), lbl))
            tx += 200
        return rects

    def _get_slider_rects(self):
        panel = self._get_settings_panel_rect()
        tracks = []
        for i in range(len(SLIDER_CONFIGS)):
            row_y = panel.y + 118 + i * 96
            track = pygame.Rect(panel.x + 30, row_y + 36, 430, 6)
            tracks.append((track, row_y))
        return panel, tracks

    def _get_gameplay_toggle_rects(self):
        panel = self._get_settings_panel_rect()
        items = [
            ("cfg_auto_rotate_board", "Auto-rotate board",
             "View games from the target engine's perspective"),
            ("cfg_hide_coords", "Hide board coordinates",
             "Hide rank (1–8) and file (a–h) labels on squares"),
            ("cfg_engine_data_tracking", "Engine Data tracking",
             "Track CPU %, RAM usage (MB), threads & NPS each game"),
            ("cfg_move_quality_elo", "Per-game Move-Quality Elo",
             "Rate Elo per game based on move accuracy & ACPL"),
        ]
        out = []
        rx = panel.x + 500
        for i, (attr, title, desc) in enumerate(items):
            r = pygame.Rect(rx, panel.y + 118 + i * 92, 430, 76)
            out.append((r, attr, title, desc))
        return out

    def _get_rgb_slider_rects(self):
        panel = self._get_settings_panel_rect()
        labels = [
            ("light", 0, "Light Square — Red"),
            ("light", 1, "Light Square — Green"),
            ("light", 2, "Light Square — Blue"),
            ("dark",  0, "Dark Square — Red"),
            ("dark",  1, "Dark Square — Green"),
            ("dark",  2, "Dark Square — Blue"),
        ]
        out = []
        for i, (which, ch_idx, lbl) in enumerate(labels):
            ry = panel.y + 220 + i * 44
            tr = pygame.Rect(panel.x + 30, ry + 22, 330, 6)
            out.append((tr, ry, which, ch_idx, lbl))
        return out

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
            warnings["time"] = (
                "Long per-move time — tournament (especially 3600+ tiers) will be slow",
                GOLD,
            )
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

    def _update_rgb_slider_from_mouse(self, idx, mx):
        sliders = self._get_rgb_slider_rects()
        tr, _, which, ch_idx, _ = sliders[idx]
        frac = max(0.0, min(1.0, (mx - tr.x) / max(1, tr.w)))
        val = max(0, min(255, int(round(frac * 255))))
        if self.board_skin != "custom":
            l_cur, d_cur = ef.resolve_board_colors(
                self.board_skin, self.custom_light_sq, self.custom_dark_sq
            )
            self.custom_light_sq = list(l_cur)
            self.custom_dark_sq = list(d_cur)
            self.board_skin = "custom"
        if which == "light":
            self.custom_light_sq[ch_idx] = val
        else:
            self.custom_dark_sq[ch_idx] = val
        self._sync_board_visuals()

    def _draw_settings_button(self, rect, label, primary=False, active=False):
        hovered = rect.collidepoint(self.mouse_pos)
        is_light = sum(BACKGROUND) > 400
        if primary:
            fill = tuple(max(0, min(255, int(c * (1.08 if hovered else 0.96)))) for c in ACCENT)
            border = tuple(max(0, min(255, c + 30)) for c in ACCENT)
            lum = 0.299 * fill[0] + 0.587 * fill[1] + 0.114 * fill[2]
            text_color = (14, 20, 26) if lum > 145 else (248, 250, 252)
        elif active:
            fill = LIST_ROW_SEL
            border = ACCENT
            text_color = TEXT_COLOR
        elif hovered:
            fill = PANEL_HOVER
            border = ACCENT
            text_color = TEXT_COLOR
        else:
            fill = (232, 237, 245) if is_light else (44, 50, 60)
            border = BORDER
            text_color = TEXT_COLOR
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, width=2 if (primary or active) else 1, border_radius=8)
        surf = _render_text(label, 14, text_color, True)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def open_settings(self, tab=0):
        self.settings_tab = tab
        self.settings_snapshot = {
            "cpu_cores":             self.cfg_cpu_cores,
            "threads":               self.cfg_threads,
            "hash":                  self.cfg_hash,
            "time":                  self.cfg_time,
            "cfg_auto_rotate_board": self.cfg_auto_rotate_board,
            "cfg_hide_coords":       self.cfg_hide_coords,
            "cfg_engine_data_tracking": self.cfg_engine_data_tracking,
            "cfg_move_quality_elo":  self.cfg_move_quality_elo,
            "theme_mode":            self.theme_mode,
            "accent_key":            self.accent_key,
            "board_skin":            self.board_skin,
            "custom_light_sq":       list(self.custom_light_sq),
            "custom_dark_sq":        list(self.custom_dark_sq),
            "piece_style":           self.piece_style,
        }
        self.dragging_slider = None
        self.dragging_rgb_slider = None
        self.state = "EDIT_SETTINGS"

    def settings_save(self):
        self._sync_board_visuals()
        self._apply_theme(self.theme_mode, self.accent_key)
        self.settings_snapshot = None
        self.dragging_slider = None
        self.dragging_rgb_slider = None
        self.state = "MENU"

    def settings_cancel(self):
        snap = self.settings_snapshot
        if snap:
            self.cfg_cpu_cores            = snap["cpu_cores"]
            self.cfg_threads              = snap["threads"]
            self.cfg_hash                 = snap["hash"]
            self.cfg_time                 = snap["time"]
            self.cfg_auto_rotate_board    = snap["cfg_auto_rotate_board"]
            self.cfg_hide_coords          = snap["cfg_hide_coords"]
            self.cfg_engine_data_tracking = snap["cfg_engine_data_tracking"]
            self.cfg_move_quality_elo     = snap["cfg_move_quality_elo"]
            self.board_skin               = snap["board_skin"]
            self.custom_light_sq          = list(snap["custom_light_sq"])
            self.custom_dark_sq           = list(snap["custom_dark_sq"])
            self.piece_style              = snap["piece_style"]
            self._sync_board_visuals()
            self._apply_theme(snap["theme_mode"], snap["accent_key"])
        self.settings_snapshot = None
        self.dragging_slider = None
        self.dragging_rgb_slider = None
        self.state = "MENU"

    def settings_reset(self):
        self.cfg_cpu_cores            = self._actual_cpu
        self.cfg_threads              = get_recommended_threads(cpu_cores=self._actual_cpu)
        self.cfg_hash                 = get_recommended_hash_mb()
        self.cfg_time                 = TIME_LIMIT
        self.cfg_auto_rotate_board    = False
        self.cfg_hide_coords          = False
        self.cfg_engine_data_tracking = False
        self.cfg_move_quality_elo     = True
        self.board_skin               = "classic_wood"
        self.custom_light_sq          = [238, 216, 183]
        self.custom_dark_sq           = [171, 122, 89]
        self.piece_style              = "classic_2tone"
        self._sync_board_visuals()
        self._apply_theme("dark", "emerald")

    def _get_board_skin_rects(self):
        panel = self._get_settings_panel_rect()
        rects = []
        for idx, key in enumerate(ef.BOARD_SKIN_ORDER):
            col = idx % 4
            row = idx // 4
            r = pygame.Rect(panel.x + 30 + col * 138, panel.y + 132 + row * 38, 130, 32)
            rects.append((r, key, ef.BOARD_SKINS[key][0]))
        return rects

    def _get_piece_style_rects(self):
        panel = self._get_settings_panel_rect()
        rects = []
        for idx, key in enumerate(ef.PIECE_STYLE_ORDER):
            col = idx % 3
            row = idx // 3
            r = pygame.Rect(panel.x + 30 + col * 162, panel.y + 506 + row * 36, 154, 30)
            rects.append((r, key, ef.PIECE_STYLES[key]))
        return rects

    def _get_theme_option_rects(self):
        panel = self._get_settings_panel_rect()
        dark_rect  = pygame.Rect(panel.x + 30, panel.y + 146, 220, 68)
        light_rect = pygame.Rect(panel.x + 270, panel.y + 146, 220, 68)
        accent_rects = []
        for idx, key in enumerate(ef.ACCENT_ORDER):
            col = idx % 3
            row = idx // 3
            r = pygame.Rect(panel.x + 30 + col * 210, panel.y + 276 + row * 72, 194, 58)
            accent_rects.append((r, key, ef.ACCENT_PRESETS[key]["label"]))
        return dark_rect, light_rect, accent_rects

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
        for tab_idx, (trect, _) in enumerate(self._get_settings_tab_rects()):
            if trect.collidepoint(pos):
                self.settings_tab = tab_idx
                self.dragging_slider = None
                self.dragging_rgb_slider = None
                return

        if self.settings_tab == 0:
            _, tracks = self._get_slider_rects()
            for i, (track, _) in enumerate(tracks):
                hit = pygame.Rect(track.x - 12, track.y - 20, track.w + 24, track.h + 40)
                if hit.collidepoint(pos):
                    self.dragging_slider = i
                    self._update_slider_from_mouse(i, pos[0])
                    return
            for rect, attr, _, _ in self._get_gameplay_toggle_rects():
                if rect.collidepoint(pos):
                    setattr(self, attr, not getattr(self, attr, False))
                    self._sync_board_visuals()
                    return

        elif self.settings_tab == 1:
            for rect, skin_key, _ in self._get_board_skin_rects():
                if rect.collidepoint(pos):
                    self.board_skin = skin_key
                    if skin_key != "custom":
                        lc, dc = ef.resolve_board_colors(skin_key)
                        self.custom_light_sq = list(lc)
                        self.custom_dark_sq = list(dc)
                    self._sync_board_visuals()
                    return
            for idx, (tr, _, _, _, _) in enumerate(self._get_rgb_slider_rects()):
                hit = pygame.Rect(tr.x - 10, tr.y - 14, tr.w + 20, tr.h + 28)
                if hit.collidepoint(pos):
                    self.dragging_rgb_slider = idx
                    self._update_rgb_slider_from_mouse(idx, pos[0])
                    return
            for rect, style_key, _ in self._get_piece_style_rects():
                if rect.collidepoint(pos):
                    self.piece_style = style_key
                    self._sync_board_visuals()
                    return

        elif self.settings_tab == 2:
            dark_rect, light_rect, accent_rects = self._get_theme_option_rects()
            if dark_rect.collidepoint(pos):
                self._apply_theme("dark", self.accent_key)
                return
            if light_rect.collidepoint(pos):
                self._apply_theme("light", self.accent_key)
                return
            for rect, akey, _ in accent_rects:
                if rect.collidepoint(pos):
                    self._apply_theme(self.theme_mode, akey)
                    return

    # ------------------------------------------------------------------
    # BROWSE ENGINE DIALOG
    # ------------------------------------------------------------------
    def _open_browse_dialog(self, mode="primary"):
        self.browse_mode = mode
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
        self.browse_path_field.select_all()
        self.browse_selected = -1
        self.browse_scroll = 0
        if not hasattr(self, "browse_show_hidden"):
            self.browse_show_hidden = False
        self.browse_hidden_count = 0
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
        hidden_count = 0
        show_hidden = getattr(self, "browse_show_hidden", False)
        self.browse_error = ""
        try:
            items = list(os.scandir(self.browse_cwd))
            dirs = []
            files = []
            for e in items:
                try:
                    if _is_hidden_entry(e) and not show_hidden:
                        hidden_count += 1
                        continue
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
        self.browse_hidden_count = hidden_count
        if self.browse_selected >= len(self.browse_entries):
            self.browse_selected = -1

    def _toggle_browse_show_hidden(self):
        prev_selected_path = None
        if 0 <= self.browse_selected < len(self.browse_entries):
            prev_selected_path = self.browse_entries[self.browse_selected][2]

        self.browse_show_hidden = not getattr(self, "browse_show_hidden", False)
        self._refresh_dir_listing()

        if prev_selected_path is not None:
            norm_prev = os.path.normpath(prev_selected_path)
            for i, (_, _, full) in enumerate(self.browse_entries):
                if os.path.normpath(full) == norm_prev:
                    self.browse_selected = i
                    self._browse_ensure_visible()
                    break
            else:
                self.browse_selected = -1
        else:
            self.browse_selected = -1

        visible_rows = BROWSE_LIST.h // BROWSE_ROW_HEIGHT
        max_scroll = max(0, len(self.browse_entries) - visible_rows)
        self.browse_scroll = max(0, min(self.browse_scroll, max_scroll))
        self._last_browse_click_time = 0.0
        self._last_browse_click_idx = -1

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
            if hasattr(self, "_accept_browsed_engine"):
                self._accept_browsed_engine(path)
            else:
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
            if hasattr(self, "_accept_browsed_engine"):
                self._accept_browsed_engine(full_path)
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
                if hasattr(self, "_accept_browsed_engine"):
                    self._accept_browsed_engine(full_path)
                else:
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
        if BROWSE_SHOW_HIDDEN_RECT.collidepoint(pos):
            self._toggle_browse_show_hidden()
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
        ctrl = bool(mods & pygame.KMOD_CTRL) or (
            sys.platform == "darwin" and bool(mods & pygame.KMOD_GUI))
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
                    if not _set_clipboard_text(field.text[a:b]):
                        self.browse_error = "Could not copy to the clipboard."
                return
            if key == pygame.K_x:
                if field.has_selection():
                    a, b = field.get_selection_range()
                    if _set_clipboard_text(field.text[a:b]):
                        field.delete_selection()
                        self.browse_selected = -1
                    else:
                        self.browse_error = "Could not copy to the clipboard; text was not cut."
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
                    self.browse_selected = -1
                    self.browse_focus = "text"
                    self.browse_error = ""
                return
            if key == pygame.K_h and sys.platform != "darwin":
                if hasattr(self, "_toggle_browse_show_hidden"):
                    self._toggle_browse_show_hidden()
                return
            if (sys.platform == "darwin" and shift
                    and (key == pygame.K_PERIOD or event.unicode in (".", ">"))):
                if hasattr(self, "_toggle_browse_show_hidden"):
                    self._toggle_browse_show_hidden()
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

    def _draw_browse_checkbox(self, rect, label, checked=False):
        hovered = rect.collidepoint(self.mouse_pos)
        fill = PANEL_HOVER if hovered else (44, 50, 60)
        border = ACCENT if (hovered or checked) else BORDER
        pygame.draw.rect(self.screen, fill, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)

        box_size = 16
        box_rect = pygame.Rect(
            rect.x + 10,
            rect.centery - box_size // 2,
            box_size,
            box_size,
        )
        if checked:
            pygame.draw.rect(self.screen, ACCENT, box_rect, border_radius=4)
            p1 = (box_rect.x + 3, box_rect.centery)
            p2 = (box_rect.x + 6, box_rect.bottom - 4)
            p3 = (box_rect.right - 3, box_rect.y + 4)
            pygame.draw.lines(self.screen, (12, 24, 18), False, [p1, p2, p3], 2)
        else:
            pygame.draw.rect(self.screen, (20, 24, 30), box_rect, border_radius=4)
            box_border = ACCENT if hovered else (110, 118, 132)
            pygame.draw.rect(self.screen, box_border, box_rect, width=1, border_radius=4)

        label_color = TEXT_COLOR if (checked or hovered) else DIM_TEXT
        surf = _render_text(label, 14, label_color, True)
        self.screen.blit(surf, (box_rect.right + 9, rect.centery - surf.get_height() // 2))

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
                  ("Navigate folders or paste a path · Cmd+V to paste · Cmd+A to select all"
                   if sys.platform == "darwin" else
                   "Navigate folders or paste a path · Ctrl+V to paste · Ctrl+A to select all"),
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
        self._draw_browse_checkbox(
            BROWSE_SHOW_HIDDEN_RECT,
            BROWSE_SHOW_HIDDEN_LABEL,
            checked=getattr(self, "browse_show_hidden", False),
        )

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
            hidden_count = getattr(self, "browse_hidden_count", 0)
            if hidden_count > 0 and not getattr(self, "browse_show_hidden", False):
                info_text += f"  ({hidden_count} hidden)"
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
                elif event.type == pygame.WINDOWFOCUSLOST:
                    self.handle_focus_lost()
            self.process_queue()
            self.draw()
            self.clock.tick(FPS)

    def _get_confirm_modal_rects(self):
        card = pygame.Rect((WINDOW_WIDTH - 460) // 2, (WINDOW_HEIGHT - 210) // 2, 460, 210)
        cancel_r = pygame.Rect(card.right - 268, card.bottom - 56, 114, 38)
        confirm_r = pygame.Rect(card.right - 142, card.bottom - 56, 122, 38)
        return card, cancel_r, confirm_r

    def handle_key_down(self, event):
        if getattr(self, "confirm_back_to_menu", False):
            if event.key == pygame.K_ESCAPE:
                self.confirm_back_to_menu = False
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.confirm_back_to_menu = False
                self.reset()
            return

        if self.state == "BROWSE_ENGINE":
            self._handle_browse_key_down(event)
        elif self.state == "EDIT_SETTINGS":
            if event.key == pygame.K_ESCAPE and hasattr(self, "settings_cancel"):
                self.settings_cancel()
        elif self.state == "RUNNING":
            if event.key == pygame.K_ESCAPE:
                self.confirm_back_to_menu = True
            elif event.key == pygame.K_m and hasattr(self, "_apply_audio_volume"):
                self.audio_muted = not getattr(self, "audio_muted", False)
                self._apply_audio_volume()
        elif self.state == "DONE" and self.error_text:
            command = bool(event.mod & pygame.KMOD_CTRL) or (
                sys.platform == "darwin" and bool(event.mod & pygame.KMOD_GUI))
            if command and event.key == pygame.K_c:
                self._copy_error_report()
            elif event.key == pygame.K_ESCAPE:
                self.reset()
        elif self.state == "DONE":
            if getattr(self, "replay_game", None) is not None:
                plies = self.replay_game.get("plies", ())
                cur_ply = getattr(self, "replay_ply", 0)
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self._set_replay_ply(max(0, cur_ply - 1))
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._set_replay_ply(min(len(plies), cur_ply + 1))
                elif event.key == pygame.K_HOME:
                    self._set_replay_ply(0)
                elif event.key == pygame.K_END:
                    self._set_replay_ply(len(plies))
                elif event.key == pygame.K_f:
                    self.replay_flipped = not bool(self._effective_replay_flipped())
                elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._close_replay_game()
                return

            if event.key == pygame.K_ESCAPE and hasattr(self, "_get_confirm_modal_rects"):
                self.confirm_back_to_menu = True
                return

            w = getattr(self, "worker", None)
            rows = (self._active_done_opponent_rows()
                    if hasattr(self, "_active_done_opponent_rows")
                    else [r for r in getattr(w, "per_opponent_results", ())
                          if r[2] + r[3] + r[4] > 0])
            visible = globals().get("RESULTS_VISIBLE_ROWS", 13)
            max_scroll = max(0, len(rows) - visible)
            cur = getattr(self, "results_scroll", 0)
            d_cur = getattr(self, "done_scroll_y", 0)
            d_max = getattr(self, "done_max_scroll", 0)
            if event.key == pygame.K_UP:
                self.results_scroll = max(0, cur - 1)
                self.done_scroll_y = max(0, d_cur - 44)
            elif event.key == pygame.K_DOWN:
                self.results_scroll = min(max_scroll, cur + 1)
                self.done_scroll_y = min(d_max, d_cur + 44)
            elif event.key == pygame.K_PAGEUP:
                self.results_scroll = max(0, cur - visible)
                self.done_scroll_y = max(0, d_cur - 280)
            elif event.key == pygame.K_PAGEDOWN:
                self.results_scroll = min(max_scroll, cur + visible)
                self.done_scroll_y = min(d_max, d_cur + 280)
            elif event.key == pygame.K_HOME:
                self.results_scroll = 0
                self.done_scroll_y = 0
            elif event.key == pygame.K_END:
                self.results_scroll = max_scroll
                self.done_scroll_y = d_max

    def handle_key_up(self, event):
        if self.state == "BROWSE_ENGINE":
            self._keys_down.discard(event.key)

    def handle_focus_lost(self):
        # KEYUP may go to another application after Alt+Tab / Command+Tab.
        # Do not let a stale V/C/etc. suppress the next clipboard shortcut.
        self._keys_down.clear()
        self.browse_drag_active = False
        self.dragging_audio_volume = False
        self.dragging_rgb_slider = None

    def handle_mouse_wheel(self, event):
        if getattr(self, "confirm_back_to_menu", False):
            return
        if self.state == "MENU":
            pl = getattr(self, "engine_playlist", ())
            if len(pl) > 6:
                cur = getattr(self, "playlist_scroll", 0) - event.y
                self.playlist_scroll = max(0, min(cur, len(pl) - 6))
        elif self.state == "RUNNING":
            w = getattr(self, "worker", None)
            entries = (w.get_schedule_snapshot()
                       if w is not None and hasattr(w, "get_schedule_snapshot") else [])
            vis = 11
            max_s = max(0, len(entries) - vis)
            self.running_opp_autoscroll = False
            cur = getattr(self, "running_opp_scroll", 0) - event.y * 2
            self.running_opp_scroll = max(0, min(cur, max_s))
        elif self.state == "DONE" and self.error_text:
            self.error_scroll = max(0, self.error_scroll - event.y * 3)
        elif self.state == "DONE":
            if getattr(self, "replay_game", None) is not None:
                plies = self.replay_game.get("plies", ())
                max_m = max(0, ((len(plies) + 1) // 2) - 16)
                cur_m = getattr(self, "replay_moves_scroll", 0) - event.y * 2
                self.replay_moves_scroll = max(0, min(cur_m, max_m))
                return
            w = getattr(self, "worker", None)
            rows = (self._active_done_opponent_rows()
                    if hasattr(self, "_active_done_opponent_rows")
                    else [r for r in getattr(w, "per_opponent_results", ())
                          if r[2] + r[3] + r[4] > 0])
            visible = globals().get("RESULTS_VISIBLE_ROWS", 13)
            max_scroll = max(0, len(rows) - visible)
            cur = getattr(self, "results_scroll", 0) - event.y * 3
            self.results_scroll = max(0, min(cur, max_scroll))
            d_max = getattr(self, "done_max_scroll", 0)
            d_cur = getattr(self, "done_scroll_y", 0) - event.y * 44
            self.done_scroll_y = max(0, min(d_cur, d_max))
        elif self.state == "BROWSE_ENGINE":
            if BROWSE_LIST.collidepoint(self.mouse_pos):
                self.browse_scroll -= event.y
                visible = BROWSE_LIST.h // BROWSE_ROW_HEIGHT
                max_scroll = max(0, len(self.browse_entries) - visible)
                self.browse_scroll = max(0, min(self.browse_scroll, max_scroll))

    def handle_click(self, pos):
        if getattr(self, "confirm_back_to_menu", False):
            _, cancel_r, confirm_r = self._get_confirm_modal_rects()
            if cancel_r.collidepoint(pos):
                self.confirm_back_to_menu = False
            elif confirm_r.collidepoint(pos):
                self.confirm_back_to_menu = False
                self.reset()
            return

        if self.state == "MENU":
            if self.browse_rect.collidepoint(pos):
                self._open_browse_dialog(mode="primary")
            elif getattr(self, "customize_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.open_settings(tab=1)
            elif getattr(self, "quick_theme_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                new_mode = "light" if getattr(self, "theme_mode", "dark") == "dark" else "dark"
                self._apply_theme(new_mode, getattr(self, "accent_key", "emerald"))
            elif getattr(self, "playlist_add_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self._open_browse_dialog(mode="playlist_add")
            elif getattr(self, "playlist_clear_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.engine_playlist = []
                self.target_path = None
                self.playlist_scroll = 0
                self.status_text = "Playlist cleared."
            elif self.start_rect.collidepoint(pos) and (self.target_path or getattr(self, "engine_playlist", None)):
                self.start_tournament()
            elif self.edit_system_rect.collidepoint(pos):
                self.open_settings(tab=0)
            else:
                for action, idx, rect in getattr(self, "_playlist_row_hitboxes", ()):
                    if rect.collidepoint(pos) and 0 <= idx < len(self.engine_playlist):
                        if action == "up" and idx > 0:
                            self.engine_playlist[idx - 1], self.engine_playlist[idx] = (
                                self.engine_playlist[idx], self.engine_playlist[idx - 1]
                            )
                            self.target_path = self.engine_playlist[0]
                        elif action == "down" and idx + 1 < len(self.engine_playlist):
                            self.engine_playlist[idx + 1], self.engine_playlist[idx] = (
                                self.engine_playlist[idx], self.engine_playlist[idx + 1]
                            )
                            self.target_path = self.engine_playlist[0]
                        elif action == "remove":
                            self.engine_playlist.pop(idx)
                            self.target_path = self.engine_playlist[0] if self.engine_playlist else None
                            self.playlist_scroll = max(0, min(self.playlist_scroll, max(0, len(self.engine_playlist) - 6)))
                        elif action == "select":
                            self.target_path = self.engine_playlist[idx]
                        return
        elif self.state == "EDIT_SETTINGS":
            self._handle_settings_click(pos)
        elif self.state == "BROWSE_ENGINE":
            self._handle_browse_click(pos)
        elif self.state == "RUNNING":
            if getattr(self, "running_back_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.confirm_back_to_menu = True
                return
            if getattr(self, "running_mute_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.audio_muted = not getattr(self, "audio_muted", False)
                self._apply_audio_volume()
                return
            vol_r = getattr(self, "running_vol_rect", pygame.Rect(0, 0, 0, 0))
            if vol_r.inflate(16, 22).collidepoint(pos):
                self.dragging_audio_volume = True
                self._set_volume_from_mouse(vol_r, pos[0])
                return
            w = getattr(self, "worker", None)
            if w is not None and hasattr(w, "toggle_skip_opponent"):
                for opp_idx, btn_rect in getattr(self, "_running_skip_hitboxes", ()):
                    if btn_rect.collidepoint(pos):
                        w.toggle_skip_opponent(opp_idx)
                        return
            follow_r = getattr(self, "_running_follow_live_rect", None)
            if follow_r is not None and follow_r.collidepoint(pos):
                self.running_opp_autoscroll = True
                return
        elif self.state == "DONE":
            if self.error_text:
                if ERROR_COPY_RECT.collidepoint(pos):
                    self._copy_error_report()
                elif ERROR_BACK_RECT.collidepoint(pos):
                    self.reset()
                return
            if self.done_start_time is not None:
                elapsed = time.time() - self.done_start_time
                if elapsed < REVEAL_DURATION:
                    return

            if getattr(self, "replay_game", None) is not None:
                if self.replay_back_rect.collidepoint(pos):
                    self._close_replay_game()
                    return
                if self.replay_flip_rect.collidepoint(pos):
                    self.replay_flipped = not bool(self._effective_replay_flipped())
                    return
                plies = self.replay_game.get("plies", ())
                for action, rect in getattr(self, "_replay_nav_rects", ()):
                    if rect.collidepoint(pos):
                        if action == "first":
                            self._set_replay_ply(0)
                        elif action == "prev":
                            self._set_replay_ply(max(0, self.replay_ply - 1))
                        elif action == "next":
                            self._set_replay_ply(min(len(plies), self.replay_ply + 1))
                        elif action == "last":
                            self._set_replay_ply(len(plies))
                        return
                for ply_num, rect in getattr(self, "_replay_move_hitboxes", ()):
                    if rect.collidepoint(pos):
                        self._set_replay_ply(ply_num)
                        return
                return

            if getattr(self, "done_back_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.confirm_back_to_menu = True
                return
            if getattr(self, "running_mute_rect", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.audio_muted = not getattr(self, "audio_muted", False)
                self._apply_audio_volume()
                return
            vol_r = getattr(self, "running_vol_rect", pygame.Rect(0, 0, 0, 0))
            if vol_r.inflate(16, 22).collidepoint(pos):
                self.dragging_audio_volume = True
                self._set_volume_from_mouse(vol_r, pos[0])
                return
            if pos[1] >= 59:
                for res_idx, rect in getattr(self, "_done_playlist_hitboxes", ()):
                    if rect.collidepoint(pos):
                        self._select_playlist_result(res_idx)
                        return
                for game_rec, rect in getattr(self, "_done_game_hitboxes", ()):
                    if rect.collidepoint(pos):
                        self._open_replay_game(game_rec)
                        return
            if self.estimated_elo is None and not getattr(self, "playlist_results", None):
                self.confirm_back_to_menu = True

    def handle_mouse_up(self, pos):
        self.dragging_audio_volume = False
        if self.state == "EDIT_SETTINGS":
            self.dragging_slider = None
            self.dragging_rgb_slider = None
        elif self.state == "BROWSE_ENGINE":
            if self.browse_drag_active:
                self.browse_drag_active = False
                field = self.browse_path_field
                if field.sel_start == field.sel_end:
                    field.clear_selection()

    def handle_mouse_motion(self, pos):
        if getattr(self, "dragging_audio_volume", False):
            self._set_volume_from_mouse(self.running_vol_rect, pos[0])
            return
        if self.state == "EDIT_SETTINGS":
            if self.dragging_slider is not None:
                self._update_slider_from_mouse(self.dragging_slider, pos[0])
            elif getattr(self, "dragging_rgb_slider", None) is not None:
                self._update_rgb_slider_from_mouse(self.dragging_rgb_slider, pos[0])
        elif self.state == "BROWSE_ENGINE" and self.browse_drag_active:
            field = self.browse_path_field
            idx = self._text_index_at(BROWSE_FIELD, field, pos[0])
            field.cursor = idx
            field.sel_end = idx
            if field.sel_start is None:
                field.sel_start = idx

    def _start_single_engine_worker(self, engine_path):
        self.target_path = engine_path
        self.progress_queue = queue.Queue()
        self.animation = None
        self.last_animated_fen = chess.STARTING_FEN
        self.last_animated_counter = 0
        self.last_move_from = None
        self.last_move_to = None
        self.last_games_played = 0
        self.last_wins         = 0
        self.last_draws        = 0
        self.last_losses       = 0
        self.running_opp_scroll = 0
        self.running_opp_autoscroll = True
        self.start_time = time.time()
        settings = {
            "threads":              self.cfg_threads,
            "hash":                 self.cfg_hash,
            "time":                 self.cfg_time,
            "engine_data_tracking": self.cfg_engine_data_tracking,
            "move_quality_elo":     self.cfg_move_quality_elo,
            "chess_clock":          30.0,
        }
        self.worker = TournamentWorker(
            engine_path,
            self.progress_queue,
            settings,
            eval_cache=self.shared_eval_cache,
        )
        self.worker.start()

    def start_tournament(self):
        self._stop_aux_workers()
        paths = list(self.engine_playlist) if self.engine_playlist else (
            [self.target_path] if self.target_path else []
        )
        if not paths:
            return
        self.active_playlist_paths = paths
        self.playlist_current_idx = 0
        self.playlist_results = []
        self.selected_result_idx = 0
        self.replay_game = None
        self.confirm_back_to_menu = False
        self.done_scroll_y = 0
        self.done_max_scroll = 0

        self.state = "RUNNING"
        self.error_text = None
        self.error_report = ""
        self.error_clipboard_status = ""
        self.error_scroll = 0
        self.results_scroll = 0
        self._error_lines = None
        self.status_text = "Starting tournament…"
        self.done_start_time = None
        self.confetti = []
        self.confetti_spawned = False
        self._elo_surface_cache = None
        self._displayed_eval_frac = 0.5
        self.shared_eval_cache = {}

        self.live_eval_worker = ef.LiveEvalWorker(
            ADJUDICATOR_PATH, protocol_cls=CompatibleUciProtocol
        )
        self.live_eval_worker.cache = self.shared_eval_cache
        self.live_eval_worker.start()
        self._start_single_engine_worker(paths[0])

    def _snapshot_finished_worker(self, estimate_payload, error_payload=None):
        w = getattr(self, "worker", None)
        est_kind = None
        est_elo = None
        ci = None
        if estimate_payload is not None:
            est_kind, est_elo = estimate_payload[0]
            ci = estimate_payload[1]
        entry = {
            "engine_name":          getattr(w, "target_name", os.path.basename(self.target_path or "Engine")),
            "engine_path":          getattr(w, "target_path", self.target_path),
            "target_config_str":    getattr(w, "target_config_str", ""),
            "estimate_kind":        est_kind,
            "estimated_elo":        est_elo,
            "confidence":           ci,
            "wins":                 getattr(w, "wins", 0),
            "draws":                getattr(w, "draws", 0),
            "losses":               getattr(w, "losses", 0),
            "games_played":         getattr(w, "games_played", 0),
            "per_opponent_results": list(getattr(w, "per_opponent_results", ())),
            "game_records":         list(getattr(w, "game_records", ())),
            "move_quality":         getattr(w, "move_quality_summary", None),
            "resource_summary":     getattr(w, "resource_summary", None),
            "high_elo_extended":    getattr(w, "high_elo_extended", False),
            "extension_start_index": getattr(w, "extension_start_index", None),
            "error_text":           error_payload["summary"] if error_payload else None,
            "error_report":         error_payload["report"] if error_payload else "",
        }
        self.playlist_results.append(entry)
        return entry

    def _select_playlist_result(self, idx):
        results = getattr(self, "playlist_results", ())
        if not (0 <= idx < len(results)):
            return
        self.selected_result_idx = idx
        sel = results[idx]
        self.estimate_kind = sel["estimate_kind"]
        self.estimated_elo = sel["estimated_elo"]
        self.confidence = sel["confidence"]
        self._elo_surface_cache = None
        rows = [r for r in sel["per_opponent_results"] if r[2] + r[3] + r[4] > 0]
        visible = globals().get("RESULTS_VISIBLE_ROWS", 13)
        self.results_scroll = (
            max(0, len(rows) - visible) if sel["high_elo_extended"] else 0
        )

    def _active_done_entry(self):
        results = getattr(self, "playlist_results", None)
        idx = getattr(self, "selected_result_idx", 0)
        if results and 0 <= idx < len(results):
            return results[idx]
        w = getattr(self, "worker", None)
        if w is None:
            return None
        return {
            "engine_name":          getattr(w, "target_name", "Target"),
            "engine_path":          getattr(w, "target_path", self.target_path),
            "target_config_str":    getattr(w, "target_config_str", ""),
            "estimate_kind":        getattr(self, "estimate_kind", None),
            "estimated_elo":        getattr(self, "estimated_elo", None),
            "confidence":           getattr(self, "confidence", None),
            "wins":                 getattr(w, "wins", 0),
            "draws":                getattr(w, "draws", 0),
            "losses":               getattr(w, "losses", 0),
            "games_played":         getattr(w, "games_played", 0),
            "per_opponent_results": list(getattr(w, "per_opponent_results", ())),
            "game_records":         list(getattr(w, "game_records", ())),
            "move_quality":         getattr(w, "move_quality_summary", None),
            "resource_summary":     getattr(w, "resource_summary", None),
            "high_elo_extended":    getattr(w, "high_elo_extended", False),
            "extension_start_index": getattr(w, "extension_start_index", None),
        }

    def _active_done_opponent_rows(self):
        entry = self._active_done_entry() if hasattr(self, "_active_done_entry") else None
        if not entry:
            return []
        return [r for r in entry.get("per_opponent_results", ()) if r[2] + r[3] + r[4] > 0]

    def _effective_replay_flipped(self):
        if getattr(self, "replay_flipped", None) is not None:
            return bool(self.replay_flipped)
        g = getattr(self, "replay_game", None)
        if g and getattr(self, "cfg_auto_rotate_board", False):
            return not bool(g.get("target_is_white", True))
        return False

    def _replay_current_fen(self):
        g = getattr(self, "replay_game", None)
        if not g:
            return chess.STARTING_FEN
        plies = g.get("plies", ())
        ply = max(0, min(int(getattr(self, "replay_ply", 0)), len(plies)))
        if ply == 0:
            return g.get("initial_fen", chess.STARTING_FEN)
        return plies[ply - 1].get("fen_after", chess.STARTING_FEN)

    def _set_replay_ply(self, ply_idx):
        g = getattr(self, "replay_game", None)
        if not g:
            return
        plies = g.get("plies", ())
        self.replay_ply = max(0, min(int(ply_idx), len(plies)))
        fen = self._replay_current_fen()
        rew = getattr(self, "replay_eval_worker", None)
        if rew is not None:
            rew.request_fen(fen)
        move_row = max(0, (self.replay_ply - 1) // 2)
        if move_row < self.replay_moves_scroll:
            self.replay_moves_scroll = move_row
        elif move_row >= self.replay_moves_scroll + 14:
            self.replay_moves_scroll = move_row - 13

    def _open_replay_game(self, game_rec):
        self.replay_game = game_rec
        self.replay_ply = 0
        self.replay_flipped = None
        self.replay_moves_scroll = 0
        if getattr(self, "replay_eval_worker", None) is None:
            strong_threads = max(2, getattr(self, "cfg_cpu_cores", 4) // 2)
            strong_hash = min(512, max(128, int(getattr(self, "cfg_hash", 256))))
            self.replay_eval_worker = ef.ReplayEvalWorker(
                ADJUDICATOR_PATH,
                threads=strong_threads,
                hash_mb=strong_hash,
                protocol_cls=CompatibleUciProtocol,
            )
            self.replay_eval_worker.start()
        self.replay_eval_worker.request_fen(self._replay_current_fen())

    def _close_replay_game(self):
        self.replay_game = None
        self.replay_flipped = None

    def process_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                if msg[0] == "status":
                    self.status_text = msg[1]
                elif msg[0] == "done":
                    if self.error_text:
                        continue  # Cleanup must not replace a fatal diagnostic.
                    estimate = msg[1]
                    if hasattr(self, "_snapshot_finished_worker"):
                        self._snapshot_finished_worker(estimate)
                        paths = getattr(self, "active_playlist_paths", ())
                        cur_idx = getattr(self, "playlist_current_idx", 0)
                        if cur_idx + 1 < len(paths):
                            self.playlist_current_idx = cur_idx + 1
                            next_path = paths[self.playlist_current_idx]
                            self.status_text = (
                                f"Playlist ({self.playlist_current_idx + 1}/{len(paths)}): "
                                f"starting {os.path.basename(next_path)}…"
                            )
                            self._start_single_engine_worker(next_path)
                            return
                        if hasattr(self, "_stop_aux_workers"):
                            self._stop_aux_workers()

                    self.state = "DONE"
                    self.done_start_time = time.time()
                    self.confetti = []
                    self.confetti_spawned = False
                    self.done_scroll_y = 0
                    if hasattr(self, "_select_playlist_result") and getattr(self, "playlist_results", None):
                        best_idx = 0
                        for idx_r, r_entry in enumerate(self.playlist_results):
                            if r_entry.get("estimated_elo") is not None:
                                best_idx = idx_r
                                break
                        self._select_playlist_result(best_idx)
                    elif estimate is None:
                        self.estimated_elo = None
                        self.estimate_kind = None
                        self.confidence = None
                        self.results_scroll = 0
                    else:
                        self.estimate_kind, self.estimated_elo = estimate[0]
                        self.confidence = estimate[1]
                        w = getattr(self, "worker", None)
                        if getattr(w, "high_elo_extended", False):
                            rows = [r for r in getattr(w, "per_opponent_results", ())
                                    if r[2] + r[3] + r[4] > 0]
                            visible = globals().get("RESULTS_VISIBLE_ROWS", 13)
                            self.results_scroll = max(0, len(rows) - visible)
                        else:
                            self.results_scroll = 0
                    if self.drumroll_sound and self.estimated_elo is not None and not self.error_text:
                        try:
                            self.drumroll_sound.play()
                        except Exception:
                            pass
                elif msg[0] == "error":
                    error = msg[1]
                    if hasattr(self, "_snapshot_finished_worker"):
                        paths = getattr(self, "active_playlist_paths", ())
                        cur_idx = getattr(self, "playlist_current_idx", 0)
                        if len(paths) > 1 and cur_idx + 1 < len(paths):
                            self._snapshot_finished_worker(None, error_payload=error)
                            self.playlist_current_idx = cur_idx + 1
                            next_path = paths[self.playlist_current_idx]
                            self.status_text = (
                                f"Engine {cur_idx + 1} failed ({error['summary']}); "
                                f"advancing to {os.path.basename(next_path)}…"
                            )
                            self._start_single_engine_worker(next_path)
                            return
                        if hasattr(self, "_stop_aux_workers"):
                            self._stop_aux_workers()
                    self.state = "DONE"
                    self.estimated_elo = None
                    self.error_text = error["summary"]
                    self.error_report = error["report"]
                    self.error_scroll = 0
                    self._error_lines = None
                    self._copy_error_report()
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
            else:
                self.animation = None
                self.last_move_from = None
                self.last_move_to = None
        if self.animation is not None and self.animation.done():
            self.animation = None

    def _play_game_sound(self, sound_key):
        sounds = getattr(self, "sounds", None) or {}
        snd = sounds.get(sound_key)
        if snd is None:
            attr_map = {
                "castle":     "castle_sound",
                "game-start": "game_start_sound",
                "game-end":   "game_end_sound",
                "move-self":  "move_sound",
                "move-check": "check_sound",
                "promote":    "promote_sound",
            }
            attr = attr_map.get(sound_key)
            if attr:
                snd = getattr(self, attr, None)
        if snd is None:
            return
        channels = getattr(self, "sound_channels", None) or {}
        ch = channels.get(sound_key)
        try:
            if ch is not None:
                ch.play(snd)
            else:
                snd.play()
        except Exception:
            pass

    def _update_game_sounds(self):
        w = self.worker
        if w is None:
            return
        events = getattr(w, "sound_events", None)
        if events is not None:
            if getattr(self, "error_text", None):
                events.clear()
                return
            batch = []
            seen = set()
            while True:
                try:
                    ev = events.popleft()
                except IndexError:
                    break
                if ev not in seen:
                    seen.add(ev)
                    batch.append(ev)
            for ev in batch:
                self._play_game_sound(ev)
            self.last_games_played = w.games_played
            self.last_wins         = w.wins
            self.last_draws        = w.draws
            self.last_losses       = w.losses
            return

        if w.games_played > self.last_games_played:
            self._play_game_sound("game-end")
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
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 20
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
        radius = 135
        for i in range(12):
            a = i * math.pi / 6
            x = cx + math.cos(a) * radius
            y = cy + math.sin(a) * radius
            diff = abs(((a - spinner_angle) % (2 * math.pi)) - math.pi)
            brightness = max(0.0, 1.0 - diff / math.pi)
            c = int(255 * brightness)
            pygame.draw.circle(self.screen, (c, int(c * 0.8), 0), (int(x), int(y)), 5)
        pulse = 0.5 + 0.5 * math.sin(elapsed * 7)
        size = int(38 + pulse * 6)
        dots = "." * ((int(elapsed * 3) % 4))
        msg = f"CALCULATING ELO{dots}"
        font = _get_font(_FONT_FAMILY, size, True)
        surf = font.render(msg, True, (255, 220, 100))
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

        # Progress bar for calculating Elo (0% -> 100%)
        calc_frac = max(0.0, min(1.0, elapsed / max(0.05, REVEAL_DURATION)))
        bar_w, bar_h = 440, 14
        bar_rect = pygame.Rect(cx - bar_w // 2, cy + 168, bar_w, bar_h)
        pygame.draw.rect(self.screen, (42, 48, 60), bar_rect, border_radius=7)
        pygame.draw.rect(self.screen, (80, 90, 110), bar_rect, width=1, border_radius=7)
        fill_w = max(8, int(round(bar_w * calc_frac))) if calc_frac > 0 else 0
        if fill_w > 0:
            pygame.draw.rect(
                self.screen,
                ACCENT,
                pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_h),
                border_radius=7,
            )
        stage_txt = (
            "Aggregating match outcomes…" if calc_frac < 0.35 else
            "Fitting maximum-likelihood Elo & 95% CI…" if calc_frac < 0.72 else
            "Finalizing per-game move-quality ratings…"
        )
        draw_text_centered(
            self.screen,
            f"{stage_txt}   ({int(round(calc_frac * 100))}%)",
            (cx, bar_rect.bottom + 18),
            15,
            (210, 218, 232),
        )

        glow_alpha = int(40 + 60 * pulse)
        halo_size = int(200 + 36 * pulse)
        halo = pygame.Surface((halo_size * 2, halo_size * 2), pygame.SRCALPHA)
        for r in range(halo_size, 0, -12):
            a = int(glow_alpha * (1 - r / halo_size))
            pygame.draw.circle(halo, (255, 200, 50, a), (halo_size, halo_size), r)
        self.screen.blit(halo, (cx - halo_size, cy - halo_size))

    def _draw_elo_pop(self, cy, pop_elapsed, cx=None, target_surf=None):
        dest = target_surf if target_surf is not None else self.screen
        elo_val = self.estimated_elo if self.estimated_elo is not None else 0.0
        elo_str = f"{elo_val:.0f}"
        if self.estimate_kind == "lower_bound":
            elo_str = f"≥ {elo_str}"
        elif self.estimate_kind == "upper_bound":
            elo_str = f"≤ {elo_str}"
        if cx is None:
            cx = WINDOW_WIDTH // 2
        cache_key = (elo_str, self.estimate_kind, GOLD)
        if self._elo_surface_cache is None or self._elo_surface_cache[0] != cache_key:
            base_font = _get_font(_FONT_FAMILY, 60, True)
            base_surf = base_font.render(elo_str, True, GOLD)
            glow_base = base_font.render(elo_str, True, (255, 180, 60))
            self._elo_surface_cache = (cache_key, base_surf, glow_base)
        _, base_surf, glow_base = self._elo_surface_cache
        bw, bh = base_surf.get_size()
        pop_t = min(1.0, pop_elapsed / ELO_POP_DURATION) if pop_elapsed < ELO_POP_DURATION else 1.0
        scale = ease_out_back(pop_t, 3.0)
        if scale > 0.05:
            halo_radius = int((bw // 2 + 70) * scale)
            if halo_radius > 4:
                halo = pygame.Surface((halo_radius * 2, halo_radius * 2), pygame.SRCALPHA)
                for r in range(halo_radius, 0, -10):
                    a = int(55 * (1 - r / halo_radius))
                    pygame.draw.circle(halo, (255, 190, 40, a),
                                       (halo_radius, halo_radius), r)
                dest.blit(halo, (cx - halo_radius, cy - halo_radius))
        for i in range(4, 0, -1):
            gs = scale * (1.0 + i * 0.09)
            gw, gh = max(1, int(bw * gs)), max(1, int(bh * gs))
            if gw > 4 and gh > 4:
                try:
                    glow = pygame.transform.scale(glow_base, (gw, gh))
                    glow.set_alpha(int(40 / i))
                    dest.blit(glow, glow.get_rect(center=(cx, cy)))
                except Exception:
                    pass
        tw, th = max(1, int(bw * scale)), max(1, int(bh * scale))
        if tw > 4 and th > 4:
            try:
                scaled = pygame.transform.smoothscale(base_surf, (tw, th))
                dest.blit(scaled, scaled.get_rect(center=(cx, cy)))
            except Exception:
                pass
        label_alpha = min(255, int(255 * max(0.0, (pop_elapsed - 0.2) / 0.4)))
        if label_alpha > 0:
            lf = _get_font(_FONT_FAMILY, 17, True)
            label = lf.render("WIN-RATE ELO", True, DIM_TEXT)
            label.set_alpha(label_alpha)
            dest.blit(label, label.get_rect(center=(cx, cy - 66)))
            if self.confidence is not None and self.estimate_kind == "ok":
                cf = _get_font(_FONT_FAMILY, 15, False)
                ci = cf.render(f"± {self.confidence:.0f}  (95% CI)",
                               True, DIM_TEXT)
                ci.set_alpha(label_alpha)
                dest.blit(ci, ci.get_rect(center=(cx, cy + 56)))

    def _draw_eval_bar(self, rect, white_cp, mate_in=None, flipped=False, badge=None):
        _ef = globals().get("ef")
        target_frac = (
            _ef.eval_bar_white_fraction(white_cp, mate_in)
            if _ef is not None else 0.5
        )
        cur_frac = getattr(self, "_displayed_eval_frac", target_frac)
        cur_frac += (target_frac - cur_frac) * 0.22
        self._displayed_eval_frac = cur_frac

        white_col = (242, 244, 248)
        black_col = (30, 33, 42)
        pygame.draw.rect(self.screen, black_col, rect, border_radius=5)
        white_h = int(round(rect.h * cur_frac))
        if flipped:
            # White at top, Black at bottom
            if white_h > 0:
                pygame.draw.rect(
                    self.screen, white_col,
                    pygame.Rect(rect.x, rect.y, rect.w, white_h),
                    border_radius=5,
                )
        else:
            # White at bottom, Black at top
            if white_h > 0:
                pygame.draw.rect(
                    self.screen, white_col,
                    pygame.Rect(rect.x, rect.bottom - white_h, rect.w, white_h),
                    border_radius=5,
                )
        mid_y = rect.centery
        pygame.draw.line(self.screen, ACCENT, (rect.x, mid_y), (rect.right - 1, mid_y), 1)
        pygame.draw.rect(self.screen, BORDER, rect, width=1, border_radius=5)

        lbl = _ef.format_eval_label(white_cp, mate_in) if _ef is not None else "0.0"
        draw_text_centered(self.screen, lbl, (rect.centerx, rect.y - 11), 11, TEXT_COLOR, bold=True)
        if badge:
            draw_text_centered(self.screen, badge, (rect.centerx, rect.bottom + 11), 10, DIM_TEXT)

    def _draw_clock_pill(self, rect, seconds_left, active=False):
        sec = max(0.0, float(seconds_left))
        mins = int(sec) // 60
        rem = sec - mins * 60
        txt = f"{mins:01d}:{rem:04.1f}" if sec < 10.0 else f"{mins:02d}:{int(rem):02d}"
        low = sec <= 5.0
        warn = 5.0 < sec <= 10.0
        if low:
            fill = (110, 32, 38) if sum(BACKGROUND) < 400 else (252, 215, 218)
            bdr = LOSS_COLOR
            tcol = LOSS_COLOR
        elif active:
            fill = LIST_ROW_SEL
            bdr = ACCENT
            tcol = GOLD if warn else TEXT_COLOR
        else:
            fill = PANEL
            bdr = BORDER
            tcol = DIM_TEXT
        pygame.draw.rect(self.screen, fill, rect, border_radius=7)
        pygame.draw.rect(self.screen, bdr, rect, width=2 if active else 1, border_radius=7)
        s = _render_text(txt, 15, tcol, True)
        self.screen.blit(s, s.get_rect(center=rect.center))

    def _draw_confirm_modal(self):
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 185))
        self.screen.blit(dim, (0, 0))
        card, cancel_r, confirm_r = self._get_confirm_modal_rects()
        draw_rounded_panel(self.screen, card, fill=PANEL, border=ACCENT, radius=14)
        draw_text(self.screen, "Return to Main Menu?",
                  (card.x + 26, card.y + 24), 22, TEXT_COLOR, bold=True)
        body = (
            "Stop the active Elo test and discard unfinished games?"
            if self.state == "RUNNING"
            else "Leave the Elo results screen and return to the main menu?"
        )
        draw_text(self.screen, body, (card.x + 26, card.y + 66), 15, DIM_TEXT)
        draw_text(self.screen, "Press Esc to stay  ·  Enter to confirm",
                  (card.x + 26, card.y + 94), 13, DIM_TEXT)
        self._draw_settings_button(cancel_r, "Cancel", primary=False)
        self._draw_settings_button(confirm_r, "Back to Menu", primary=True)

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
        if getattr(self, "confirm_back_to_menu", False) and hasattr(self, "_draw_confirm_modal"):
            self._draw_confirm_modal()
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
        draw_text(self.screen, "Settings & Appearance", (panel.x + 30, panel.y + 18),
                  24, ACCENT, bold=True)

        # Tabs
        for tab_idx, (trect, tlabel) in enumerate(self._get_settings_tab_rects()):
            self._draw_settings_button(
                trect, tlabel, primary=False, active=(self.settings_tab == tab_idx)
            )
        pygame.draw.line(self.screen, BORDER,
                         (panel.x + 30, panel.y + 100),
                         (panel.right - 30, panel.y + 100), 1)

        if self.settings_tab == 0:
            warnings = self._get_setting_warnings()
            for i, (track, row_y) in enumerate(tracks):
                key, label, _, _, _, _ = SLIDER_CONFIGS[i]
                value = getattr(self, f"cfg_{key}")
                vmin, vmax, _, _ = self._slider_params(key)
                draw_text(self.screen, label, (track.x, row_y),
                          15, TEXT_COLOR, bold=True)
                val_str = self._format_slider_value(key)
                vsurf = _render_text(val_str, 16, GOLD, True)
                self.screen.blit(vsurf, (track.right - vsurf.get_width(), row_y - 1))
                frac = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
                fill_color = warnings[key][1] if key in warnings else ACCENT
                pygame.draw.rect(self.screen, BORDER, track, border_radius=3)
                fill_w = int(track.w * frac)
                if fill_w > 0:
                    pygame.draw.rect(self.screen, fill_color,
                                     pygame.Rect(track.x, track.y, fill_w, track.h),
                                     border_radius=3)
                knob_x = track.x + fill_w
                knob_y = track.centery
                pygame.draw.circle(self.screen, BACKGROUND, (knob_x, knob_y), 10)
                pygame.draw.circle(self.screen, fill_color, (knob_x, knob_y), 8)
                if key in warnings:
                    wtext, wcolor = warnings[key]
                    draw_text(self.screen, wtext, (track.x, row_y + 52), 12, wcolor)

            # Right-side boolean toggles
            for rect, attr, title, desc in self._get_gameplay_toggle_rects():
                val = bool(getattr(self, attr, False))
                hov = rect.collidepoint(self.mouse_pos)
                pygame.draw.rect(
                    self.screen,
                    LIST_ROW_SEL if val else (PANEL_HOVER if hov else FIELD_BG),
                    rect, border_radius=10,
                )
                pygame.draw.rect(
                    self.screen, ACCENT if val else BORDER,
                    rect, width=2 if val else 1, border_radius=10,
                )
                chk = pygame.Rect(rect.right - 52, rect.y + 18, 36, 20)
                pygame.draw.rect(self.screen, ACCENT if val else BORDER, chk, border_radius=10)
                kx = chk.right - 10 if val else chk.x + 10
                pygame.draw.circle(self.screen, (250, 250, 252), (kx, chk.centery), 7)
                draw_text(self.screen, title, (rect.x + 16, rect.y + 14), 15, TEXT_COLOR, bold=True)
                draw_text(self.screen, desc, (rect.x + 16, rect.y + 42), 12, DIM_TEXT)

        elif self.settings_tab == 1:
            draw_text(self.screen, "BOARD SKINS (PREMADE & CUSTOM)",
                      (panel.x + 30, panel.y + 110), 13, ACCENT, bold=True)
            for rect, skin_key, label in self._get_board_skin_rects():
                self._draw_settings_button(
                    rect, label, active=(self.board_skin == skin_key)
                )

            l_col, d_col = ef.resolve_board_colors(
                self.board_skin, self.custom_light_sq, self.custom_dark_sq
            )
            for tr, ry, which, ch_idx, lbl in self._get_rgb_slider_rects():
                c_val = l_col[ch_idx] if which == "light" else d_col[ch_idx]
                draw_text(self.screen, f"{lbl}: {c_val}", (tr.x, ry), 13, TEXT_COLOR)
                pygame.draw.rect(self.screen, BORDER, tr, border_radius=3)
                fw = int(round(tr.w * (c_val / 255.0)))
                ch_col = ((230, 95, 95), (95, 205, 125), (95, 155, 240))[ch_idx]
                if fw > 0:
                    pygame.draw.rect(self.screen, ch_col,
                                     pygame.Rect(tr.x, tr.y, fw, tr.h), border_radius=3)
                pygame.draw.circle(self.screen, ch_col, (tr.x + fw, tr.centery), 7)

            draw_text(self.screen, "PIECE STYLE",
                      (panel.x + 30, panel.y + 484), 13, ACCENT, bold=True)
            for rect, style_key, label in self._get_piece_style_rects():
                self._draw_settings_button(
                    rect, label, active=(self.piece_style == style_key)
                )

            # Live preview chessboard
            prev_size = 256
            prev_pos = (panel.right - prev_size - 56, panel.y + 176)
            draw_text(self.screen, "LIVE PREVIEW",
                      (prev_pos[0], prev_pos[1] - 24), 13, GOLD, bold=True)
            preview_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 2 3"
            draw_board(
                self.screen, preview_fen, prev_pos,
                flipped=self.cfg_auto_rotate_board,
                show_coords=not self.cfg_hide_coords,
                light_col=l_col, dark_col=d_col,
                piece_style=self.piece_style,
                board_size=prev_size,
            )
            pygame.draw.rect(
                self.screen, BORDER,
                pygame.Rect(prev_pos[0] - 2, prev_pos[1] - 2, prev_size + 4, prev_size + 4),
                width=2,
            )

        elif self.settings_tab == 2:
            draw_text(self.screen, "APPEARANCE MODE",
                      (panel.x + 30, panel.y + 118), 13, ACCENT, bold=True)
            dark_rect, light_rect, accent_rects = self._get_theme_option_rects()
            self._draw_settings_button(
                dark_rect, "Dark Mode", active=(self.theme_mode == "dark")
            )
            self._draw_settings_button(
                light_rect, "Light Mode", active=(self.theme_mode == "light")
            )

            draw_text(self.screen, "ACCENT COLOR",
                      (panel.x + 30, panel.y + 244), 13, ACCENT, bold=True)
            for rect, akey, label in accent_rects:
                preset = ef.ACCENT_PRESETS[akey]
                swatch = preset["light"] if self.theme_mode == "light" else preset["dark"]
                sel = (self.accent_key == akey)
                hov = rect.collidepoint(self.mouse_pos)
                pygame.draw.rect(
                    self.screen,
                    LIST_ROW_SEL if sel else (PANEL_HOVER if hov else FIELD_BG),
                    rect, border_radius=10,
                )
                pygame.draw.rect(
                    self.screen, swatch if sel else BORDER,
                    rect, width=2 if sel else 1, border_radius=10,
                )
                pygame.draw.circle(self.screen, swatch, (rect.x + 26, rect.centery), 12)
                draw_text(self.screen, label, (rect.x + 48, rect.centery - 9),
                          15, TEXT_COLOR, bold=sel)

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
        knight_font = _get_piece_font(68)
        try:
            knight = knight_font.render("♞", True, ACCENT)
        except Exception:
            knight = None
        title_font = _get_font(_FONT_FAMILY, 64, True)
        title_surf = title_font.render("Eloify", True, ACCENT)
        th = title_surf.get_height()
        kx = 50
        if knight is not None:
            ky = 26 + (th - knight.get_height()) // 2
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
            (tx - 30, 22 + (th - glow_copy.get_height()) // 2 + 4))
        self.screen.blit(title_surf, (tx, 26))

        qt_rect = getattr(self, "quick_theme_rect", None)
        if qt_rect is not None and hasattr(self, "_draw_settings_button"):
            mode_lbl = "☀ Light Mode" if getattr(self, "theme_mode", "dark") == "dark" else "🌙 Dark Mode"
            self._draw_settings_button(qt_rect, mode_lbl)

        draw_text(self.screen, "Chess Engine Elo Tester  ·  Match & Move-Quality Rating Suite",
                  (50, 114), 18, DIM_TEXT)
        pygame.draw.line(self.screen, BORDER,
                         (50, 146), (WINDOW_WIDTH - 50, 146), 1)

        # Left column: SYSTEM + ENGINE POOL
        tracking_lbl = "ON" if getattr(self, "cfg_engine_data_tracking", False) else "OFF"
        left_rows = [
            ("CPU / Threads", f"{self.cfg_cpu_cores} cores  ·  {self.cfg_threads}T", TEXT_COLOR),
            ("Hash / Move",   f"{int(self.cfg_hash)} MB  ·  {self.cfg_time:.2f}s", TEXT_COLOR),
            ("Board / Pieces", f"{ef.BOARD_SKINS.get(getattr(self, 'board_skin', 'classic_wood'), ('Classic',))[0]} · {ef.PIECE_STYLES.get(getattr(self, 'piece_style', 'classic_2tone'), '2-Tone')}", TEXT_COLOR)
            if globals().get("ef") is not None else ("Hash / engine", f"{int(self.cfg_hash)} MB", TEXT_COLOR),
            ("Data tracking", tracking_lbl, ACCENT if tracking_lbl == "ON" else DIM_TEXT),
        ]
        sys_rect = pygame.Rect(50, 168, 450, 164)
        self._draw_stat_panel(sys_rect, "SYSTEM & SETTINGS", left_rows, accent=ACCENT)
        self.edit_system_rect = pygame.Rect(sys_rect.right - 78, sys_rect.y + 10, 58, 24)
        self._draw_edit_button(self.edit_system_rect)

        ext_tier_count, ext_max_elo = get_pool_max_extended_elo()
        base_games = len(OPPONENTS) * GAMES_PER_OPPONENT
        ext_games = ext_tier_count * GAMES_PER_OPPONENT
        opp_value = (f"{len(OPPONENTS)} (+{ext_tier_count} top)"
                     if ext_tier_count > 0 else str(len(OPPONENTS)))
        games_value = (f"{base_games} (+{ext_games} top)"
                       if ext_games > 0 else str(base_games))
        pool_rows = [
            ("Opponents",        opp_value, TEXT_COLOR),
            ("Games / opponent", f"{GAMES_PER_OPPONENT}  (30s chess clock)", TEXT_COLOR),
            ("Total games",      games_value, GOLD),
            ("Draw rules",       "3-fold rep  ·  50-move rule", TEXT_COLOR),
        ]
        if OPPONENTS:
            lo = min(r for _, r in OPPONENTS)
            hi = max(max(r for _, r in OPPONENTS), ext_max_elo)
            pool_rows.append(("Elo scale", f"{lo} – {hi}", ACCENT))
        self._draw_stat_panel(pygame.Rect(50, 348, 450, 188),
                              "ENGINE POOL", pool_rows, accent=GOLD)

        # Right column: ENGINE PLAYLIST ("NEXT IN LINE")
        pl_panel = pygame.Rect(524, 168, WINDOW_WIDTH - 574, 368)
        pygame.draw.rect(self.screen, PANEL, pl_panel, border_radius=12)
        pygame.draw.rect(self.screen, BORDER, pl_panel, width=1, border_radius=12)
        draw_text(self.screen, "ENGINE PLAYLIST  (NEXT IN LINE)",
                  (pl_panel.x + 20, pl_panel.y + 15), 14, ACCENT, bold=True)
        self.playlist_add_rect = pygame.Rect(pl_panel.right - 196, pl_panel.y + 10, 108, 26)
        self.playlist_clear_rect = pygame.Rect(pl_panel.right - 80, pl_panel.y + 10, 62, 26)
        if hasattr(self, "_draw_settings_button"):
            self._draw_settings_button(self.playlist_add_rect, "+ Add Engine", primary=True)
            self._draw_settings_button(self.playlist_clear_rect, "Clear", primary=False)
        pygame.draw.line(self.screen, BORDER,
                         (pl_panel.x + 20, pl_panel.y + 44),
                         (pl_panel.right - 20, pl_panel.y + 44), 1)

        playlist = getattr(self, "engine_playlist", None) or (
            [self.target_path] if self.target_path else []
        )
        self._playlist_row_hitboxes = []
        if not playlist:
            draw_text_centered(
                self.screen,
                "No engines queued yet.",
                (pl_panel.centerx, pl_panel.centery - 14), 17, DIM_TEXT, bold=True,
            )
            draw_text_centered(
                self.screen,
                "Click 'Browse Engine' or '+ Add Engine' to queue multiple engines in line.",
                (pl_panel.centerx, pl_panel.centery + 16), 13, DIM_TEXT,
            )
        else:
            vis = 6
            p_scroll = max(0, min(getattr(self, "playlist_scroll", 0), max(0, len(playlist) - vis)))
            self.playlist_scroll = p_scroll
            for row_i, p_path in enumerate(playlist[p_scroll:p_scroll + vis]):
                abs_i = p_scroll + row_i
                ry = pl_panel.y + 54 + row_i * 48
                rrect = pygame.Rect(pl_panel.x + 16, ry, pl_panel.w - 32, 42)
                is_first = (abs_i == 0)
                row_sel_bg = globals().get("LIST_ROW_SEL", PANEL_HOVER)
                field_bg = globals().get("FIELD_BG", PANEL)
                pygame.draw.rect(
                    self.screen,
                    row_sel_bg if is_first else field_bg,
                    rrect, border_radius=8,
                )
                pygame.draw.rect(
                    self.screen, ACCENT if is_first else BORDER,
                    rrect, width=1, border_radius=8,
                )
                badge = "NEXT UP" if is_first else f"#{abs_i + 1}"
                draw_text(self.screen, badge, (rrect.x + 12, rrect.y + 12),
                          12, ACCENT if is_first else DIM_TEXT, bold=True)
                bname = os.path.basename(p_path)
                disp = bname if len(bname) <= 36 else bname[:33] + "…"
                draw_text(self.screen, disp, (rrect.x + 82, rrect.y + 11),
                          15, TEXT_COLOR, bold=is_first)

                if hasattr(self, "_playlist_row_hitboxes") and getattr(self, "engine_playlist", None):
                    up_r = pygame.Rect(rrect.right - 106, rrect.y + 8, 28, 26)
                    dn_r = pygame.Rect(rrect.right - 74, rrect.y + 8, 28, 26)
                    rm_r = pygame.Rect(rrect.right - 40, rrect.y + 8, 30, 26)
                    for btn_r, sym, col in (
                        (up_r, "↑", TEXT_COLOR if abs_i > 0 else DIM_TEXT),
                        (dn_r, "↓", TEXT_COLOR if abs_i + 1 < len(playlist) else DIM_TEXT),
                        (rm_r, "✕", LOSS_COLOR),
                    ):
                        pygame.draw.rect(self.screen, PANEL, btn_r, border_radius=5)
                        pygame.draw.rect(self.screen, BORDER, btn_r, width=1, border_radius=5)
                        s = _render_text(sym, 13, col, True)
                        self.screen.blit(s, s.get_rect(center=btn_r.center))
                    self._playlist_row_hitboxes.append(("up", abs_i, up_r))
                    self._playlist_row_hitboxes.append(("down", abs_i, dn_r))
                    self._playlist_row_hitboxes.append(("remove", abs_i, rm_r))

        # Status bar
        status_rect = pygame.Rect(50, 552, WINDOW_WIDTH - 100, 98)
        pygame.draw.rect(self.screen, PANEL, status_rect, border_radius=12)
        pygame.draw.rect(self.screen, BORDER, status_rect, width=1, border_radius=12)
        draw_text(self.screen, "STATUS",
                  (status_rect.x + 20, status_rect.y + 12), 13, ACCENT, bold=True)
        draw_text(self.screen, self.status_text,
                  (status_rect.x + 20, status_rect.y + 36), 17, TEXT_COLOR)
        draw_text(self.screen, "Live Eval Adjudicator: " + os.path.basename(ADJUDICATOR_PATH) + " (low-thread / low-hash)",
                  (status_rect.x + 20, status_rect.y + 66), 13, DIM_TEXT)

        can_start = bool(self.target_path or getattr(self, "engine_playlist", None))
        start_lbl = (
            f"Start Playlist ({len(playlist)})"
            if len(playlist) > 1 else "Start Test"
        )
        self._draw_menu_button(self.browse_rect, "Browse Engine",
                               enabled=True, primary=False)
        cust_r = getattr(self, "customize_rect", None)
        if cust_r is not None:
            self._draw_menu_button(cust_r, "Settings & Customize",
                                   enabled=True, primary=False)
        self._draw_menu_button(self.start_rect, start_lbl,
                               enabled=can_start, primary=True)

        draw_text_centered(
            self.screen,
            "Eloify  ·  Built for chess engine developers",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 20),
            13, DIM_TEXT)

    def draw_running(self):
        w = self.worker
        if w is None:
            return
        self._update_animation()
        _ef = globals().get("ef")

        # Update non-blocking live evaluation worker with latest board FEN
        lew = getattr(self, "live_eval_worker", None)
        if lew is not None:
            lew.request_fen(w.current_fen_shared)
            eval_cp, eval_mate = lew.get_eval(w.current_fen_shared)
        elif _ef is not None:
            eval_cp, eval_mate = _ef.evaluate_board_static_cp(_get_board(w.current_fen_shared))
        else:
            eval_cp, eval_mate = (0, None)

        # Top header bar: Back to Menu + Title + Progress & ETA + Mute/Volume
        back_r = getattr(self, "running_back_rect", pygame.Rect(20, 18, 112, 34))
        if hasattr(self, "_draw_settings_button"):
            self._draw_settings_button(back_r, "← Menu", primary=False)

        in_extension = (getattr(w, "high_elo_extended", False)
                        and w.current_opponent_index >= len(OPPONENTS))
        pl_paths = getattr(self, "active_playlist_paths", ())
        pl_idx = getattr(self, "playlist_current_idx", 0)
        pl_prefix = f"[{pl_idx + 1}/{len(pl_paths)}] " if len(pl_paths) > 1 else ""
        header_title = pl_prefix + (
            "High-Elo Extension (3600+)" if in_extension else "Tournament in Progress"
        )
        header_color = GOLD if in_extension else ACCENT
        draw_text(self.screen, header_title, (146, 14), 22, header_color, bold=True)

        elapsed_s = max(0.0, time.time() - self.start_time) if self.start_time else 0.0
        elapsed_i = int(elapsed_s)
        elapsed_str = f"{elapsed_i // 60:02d}:{elapsed_i % 60:02d}"
        eta_str = "—"
        if _ef is not None:
            rem_engines = max(0, len(pl_paths) - (pl_idx + 1)) if len(pl_paths) > 1 else 0
            eta_sec = _ef.estimate_tournament_eta_seconds(
                elapsed_s,
                w.games_played,
                w.total_games,
                time_per_move=getattr(self, "cfg_time", TIME_LIMIT),
                current_move_number=getattr(w, "current_move_number", 0),
                extra_playlist_engines=rem_engines,
                base_pool_games=len(OPPONENTS) * GAMES_PER_OPPONENT,
            )
            eta_str = _ef.format_eta(eta_sec)

        frac = (w.games_played / w.total_games) if w.total_games else 0.0
        pbar = pygame.Rect(514, 20, 448, 12)
        pygame.draw.rect(self.screen, PANEL, pbar, border_radius=6)
        pygame.draw.rect(self.screen, BORDER, pbar, width=1, border_radius=6)
        if frac > 0:
            pygame.draw.rect(
                self.screen, ACCENT,
                pygame.Rect(pbar.x, pbar.y, max(4, int(pbar.w * min(1.0, frac))), pbar.h),
                border_radius=6,
            )
        draw_text(
            self.screen,
            f"Game {min(w.games_played + 1, max(1, w.total_games))}/{w.total_games} ({frac:.0%})   ·   Elapsed {elapsed_str}   ·   ETA {eta_str}",
            (514, 38), 13, DIM_TEXT,
        )
        draw_text(self.screen, f"{w.target_name}  vs  {w.opponent_name} ({w.opponent_rating})",
                  (146, 42), 14, TEXT_COLOR)

        if hasattr(self, "_draw_audio_controls"):
            self._draw_audio_controls(self.running_mute_rect, self.running_vol_rect)

        pygame.draw.line(self.screen, BORDER, (18, 68), (WINDOW_WIDTH - 18, 68), 1)

        # Board orientation (auto-rotate to Target's perspective if enabled)
        flipped = bool(getattr(self, "cfg_auto_rotate_board", False) and not w.target_is_white)

        # Live Evaluation Bar beside the board
        eval_rect = pygame.Rect(20, BOARD_POS[1], 24, BOARD_SIZE)
        if hasattr(self, "_draw_eval_bar"):
            self._draw_eval_bar(eval_rect, eval_cp, eval_mate, flipped=flipped, badge="EVAL")

        # Top & Bottom Player Strips + 30s Chess Clocks
        w_clk, b_clk = w.get_live_clocks() if hasattr(w, "get_live_clocks") else (30.0, 30.0)
        active_turn = getattr(w, "clock_active_color", None)
        top_is_white = bool(flipped)
        bot_is_white = not bool(flipped)

        for is_top, side_white, strip_y in (
            (True, top_is_white, BOARD_POS[1] - 42),
            (False, bot_is_white, BOARD_POS[1] + BOARD_SIZE + 8),
        ):
            srect = pygame.Rect(BOARD_POS[0], strip_y, BOARD_SIZE, 34)
            pygame.draw.rect(self.screen, PANEL, srect, border_radius=8)
            pygame.draw.rect(self.screen, BORDER, srect, width=1, border_radius=8)
            is_target_side = (side_white == bool(w.target_is_white))
            pname = w.target_name if is_target_side else f"{w.opponent_name} ({w.opponent_rating})"
            role_tag = "TARGET" if is_target_side else "OPP"
            dot_col = (244, 244, 248) if side_white else (22, 24, 30)
            pygame.draw.circle(self.screen, dot_col, (srect.x + 16, srect.centery), 7)
            pygame.draw.circle(self.screen, BORDER, (srect.x + 16, srect.centery), 7, 1)
            p_disp = pname if len(pname) <= 34 else pname[:31] + "…"
            draw_text(self.screen, f"[{role_tag}] {p_disp}",
                      (srect.x + 30, srect.y + 8), 14,
                      ACCENT if is_target_side else TEXT_COLOR, bold=is_target_side)
            clk_val = w_clk if side_white else b_clk
            clk_rect = pygame.Rect(srect.right - 88, srect.y + 4, 82, 26)
            if hasattr(self, "_draw_clock_pill"):
                self._draw_clock_pill(clk_rect, clk_val, active=(active_turn is side_white))

        # Chess Board
        last_move = None
        if self.last_move_from is not None and self.last_move_to is not None:
            last_move = (self.last_move_from, self.last_move_to)
        draw_board(
            self.screen, w.current_fen_shared, BOARD_POS,
            self.animation, last_move=last_move,
            flipped=flipped,
            show_coords=not getattr(self, "cfg_hide_coords", False),
        )
        pygame.draw.rect(self.screen, BORDER,
                         pygame.Rect(BOARD_POS[0] - 2, BOARD_POS[1] - 2,
                                     BOARD_SIZE + 4, BOARD_SIZE + 4),
                         width=2)

        # Footer below board: moves + optional Engine Data Tracking
        foot_rect = pygame.Rect(20, 622, 478, 138)
        draw_rounded_panel(self.screen, foot_rect)
        opening_label = getattr(w, "current_opening_name", "")
        mv_hdr = f"Move {w.current_move_number}  ·  Last: {w.last_move_san or '—'}"
        if opening_label:
            mv_hdr += f"  ·  {opening_label}"
        draw_text(self.screen, mv_hdr, (foot_rect.x + 14, foot_rect.y + 10), 14, TEXT_COLOR, bold=True)
        recent = " ".join(w.recent_moves[-8:]) if w.recent_moves else "—"
        draw_text(self.screen, f"Moves: {recent}", (foot_rect.x + 14, foot_rect.y + 32), 13, DIM_TEXT)

        if getattr(self, "cfg_engine_data_tracking", False):
            rs = getattr(w, "resource_summary", None) or {}
            cpu_now = rs.get("live_cpu_pct", 0.0)
            cpu_pk  = rs.get("peak_cpu_pct", 0.0)
            ram_now = rs.get("live_ram_mb", 0.0)
            ram_pk  = rs.get("peak_ram_mb", 0.0)
            thr_n   = rs.get("live_threads", getattr(self, "cfg_threads", 1))
            nps_v   = rs.get("live_nps", 0)
            nps_str = f"{nps_v / 1e6:.2f}M" if nps_v >= 1_000_000 else (f"{nps_v / 1e3:.0f}k" if nps_v >= 1000 else str(nps_v))
            pygame.draw.line(self.screen, BORDER,
                             (foot_rect.x + 14, foot_rect.y + 58),
                             (foot_rect.right - 14, foot_rect.y + 58), 1)
            draw_text(self.screen, "ENGINE DATA TRACKING",
                      (foot_rect.x + 14, foot_rect.y + 66), 12, ACCENT, bold=True)
            draw_text(
                self.screen,
                f"CPU: {cpu_now:.1f}% (Peak {cpu_pk:.0f}%)   ·   RAM: {ram_now:.1f} MB (Peak {ram_pk:.1f} MB)",
                (foot_rect.x + 14, foot_rect.y + 86), 13, TEXT_COLOR,
            )
            draw_text(
                self.screen,
                f"OS Threads: {thr_n}   ·   UCI Speed: {nps_str} nps",
                (foot_rect.x + 14, foot_rect.y + 108), 13, DIM_TEXT,
            )
        else:
            draw_text(self.screen, self.status_text[:66],
                      (foot_rect.x + 14, foot_rect.y + 68), 13, DIM_TEXT)
            if len(pl_paths) > 1 and pl_idx + 1 < len(pl_paths):
                nxt = os.path.basename(pl_paths[pl_idx + 1])
                draw_text(self.screen, f"Next in playlist: {nxt}",
                          (foot_rect.x + 14, foot_rect.y + 96), 13, GOLD, bold=True)

        # Middle Matchup Column
        mid_panel = pygame.Rect(514, 92, 330, 668)
        draw_rounded_panel(self.screen, mid_panel)
        mx, my = mid_panel.x + 16, mid_panel.y + 14
        mw = mid_panel.w - 32

        draw_section(self.screen, "TARGET ENGINE", (mx, my), width=mw)
        draw_text(self.screen, w.target_name[:32], (mx, my + 24), 17, TEXT_COLOR, bold=True)
        draw_text(self.screen, f"Config: {w.target_config_str}", (mx, my + 46), 13, DIM_TEXT)
        draw_text(self.screen, f"W {w.wins}", (mx, my + 70), 17, WIN_COLOR, bold=True)
        draw_text(self.screen, f"D {w.draws}", (mx + 74, my + 70), 17, DRAW_COLOR, bold=True)
        draw_text(self.screen, f"L {w.losses}", (mx + 148, my + 70), 17, LOSS_COLOR, bold=True)

        mq_sum = getattr(w, "move_quality_summary", None)
        if mq_sum:
            draw_text(
                self.screen,
                f"Move-Quality Elo: {mq_sum['move_quality_elo']:.0f}  ({mq_sum['accuracy_pct']:.1f}% acc · {mq_sum['acpl']:.1f} ACPL)",
                (mx, my + 98), 13, GOLD, bold=True,
            )
        else:
            draw_text(self.screen, "Move-Quality Elo: awaiting completed game…",
                      (mx, my + 98), 13, DIM_TEXT)

        draw_section(self.screen, "CURRENT OPPONENT", (mx, my + 134), width=mw)
        draw_text(self.screen, f"{w.opponent_name[:26]}", (mx, my + 158), 16, TEXT_COLOR, bold=True)
        draw_text(self.screen, f"Rating: {w.opponent_rating} Elo  (Scale 300–4010)",
                  (mx, my + 180), 13, ACCENT, bold=True)
        if _ef is not None and w.opponent_rating > 0:
            pal = self._current_palette() if hasattr(self, "_current_palette") else {"mode": "dark", "ACCENT": ACCENT, "GOLD": GOLD, "TEXT_COLOR": TEXT_COLOR, "DIM_TEXT": DIM_TEXT}
            _ef.draw_elo_scale_bar(
                self.screen,
                pygame.Rect(mx, my + 202, mw, 16),
                w.opponent_rating,
                pal,
                show_endpoints=True,
                font_getter=lambda sz, bold=False: _get_font(_FONT_FAMILY, sz, bold=bold),
            )
        draw_text(self.screen, f"Config: {w.opponent_config_str}",
                  (mx, my + 236), 12, DIM_TEXT)

        draw_section(self.screen, "LAST GAME", (mx, my + 268), width=mw)
        draw_text(self.screen, w.last_game_result or "—",
                  (mx, my + 292), 15, TEXT_COLOR, bold=True)
        last_mq = getattr(w, "last_game_move_quality", None)
        if last_mq:
            draw_text(
                self.screen,
                f"Game Move Elo: {last_mq['move_quality_elo']:.0f}  ·  Accuracy {last_mq['accuracy_pct']:.1f}%",
                (mx, my + 316), 13, ACCENT,
            )

        draw_section(self.screen, "PLAYLIST & STATUS", (mx, my + 354), width=mw)
        if len(pl_paths) > 1:
            for q_i, qp in enumerate(pl_paths[:6]):
                q_tag = "✓" if q_i < pl_idx else ("▶" if q_i == pl_idx else f"{q_i + 1}.")
                q_col = WIN_COLOR if q_i < pl_idx else (ACCENT if q_i == pl_idx else DIM_TEXT)
                draw_text(
                    self.screen,
                    f"{q_tag} {os.path.basename(qp)[:30]}",
                    (mx, my + 378 + q_i * 22), 13, q_col, bold=(q_i == pl_idx),
                )
            draw_text(self.screen, self.status_text[:42], (mx, my + 520), 12, DIM_TEXT)
        else:
            draw_text(self.screen, "Single-engine test active", (mx, my + 380), 14, TEXT_COLOR)
            draw_text(self.screen, "Rules: 3-fold rep · 50-move · 30s clock", (mx, my + 404), 12, DIM_TEXT)
            draw_text(self.screen, self.status_text[:42], (mx, my + 432), 12, DIM_TEXT)

        # Right Column: Scrollable Opponents Progress & Upcoming Skip Menu
        opp_panel = pygame.Rect(858, 92, 362, 668)
        draw_rounded_panel(self.screen, opp_panel)
        draw_text(self.screen, "OPPONENTS PROGRESS",
                  (opp_panel.x + 14, opp_panel.y + 12), 14, ACCENT, bold=True)
        draw_text(self.screen, "Scroll ↑ past  ·  Skip upcoming ↓",
                  (opp_panel.x + 14, opp_panel.y + 32), 12, DIM_TEXT)
        self._running_follow_live_rect = None
        if not getattr(self, "running_opp_autoscroll", True) and hasattr(self, "_draw_settings_button"):
            fl_r = pygame.Rect(opp_panel.right - 76, opp_panel.y + 10, 62, 22)
            self._draw_settings_button(fl_r, "Live", active=True)
            self._running_follow_live_rect = fl_r
        pygame.draw.line(self.screen, BORDER,
                         (opp_panel.x + 12, opp_panel.y + 52),
                         (opp_panel.right - 12, opp_panel.y + 52), 1)

        entries = (
            w.get_schedule_snapshot()
            if hasattr(w, "get_schedule_snapshot")
            else []
        )
        vis_rows = 11
        max_opp_scroll = max(0, len(entries) - vis_rows)
        if getattr(self, "running_opp_autoscroll", True):
            playing_pos = next(
                (i for i, e in enumerate(entries) if e["status"] == "playing"),
                getattr(w, "current_opponent_index", 0),
            )
            self.running_opp_scroll = max(0, min(playing_pos - 3, max_opp_scroll))
        else:
            self.running_opp_scroll = max(
                0, min(getattr(self, "running_opp_scroll", 0), max_opp_scroll)
            )

        self._running_skip_hitboxes = []
        pal = (
            self._current_palette()
            if hasattr(self, "_current_palette")
            else {"mode": "dark", "ACCENT": ACCENT, "GOLD": GOLD, "TEXT_COLOR": TEXT_COLOR, "DIM_TEXT": DIM_TEXT}
        )
        row_h = 54
        start_y = opp_panel.y + 58
        for view_i, entry in enumerate(entries[self.running_opp_scroll:self.running_opp_scroll + vis_rows]):
            ry = start_y + view_i * row_h
            rrect = pygame.Rect(opp_panel.x + 10, ry, opp_panel.w - 26, row_h - 4)
            st = entry["status"]
            is_live = (st == "playing")
            row_bg = (globals().get("LIST_ROW_SEL", PANEL_HOVER)
                      if is_live else globals().get("FIELD_BG", PANEL))
            row_bdr = ACCENT if is_live else BORDER
            pygame.draw.rect(self.screen, row_bg, rrect, border_radius=7)
            pygame.draw.rect(self.screen, row_bdr, rrect, width=2 if is_live else 1, border_radius=7)

            ename = entry["name"]
            edisp = ename if len(ename) <= 22 else ename[:20] + "…"
            name_col = DIM_TEXT if st in ("skipped", "unavailable") else TEXT_COLOR
            draw_text(self.screen, f"{edisp}  ({entry['rating']})",
                      (rrect.x + 10, rrect.y + 6), 13, name_col, bold=is_live)

            if _ef is not None:
                _ef.draw_elo_scale_bar(
                    self.screen,
                    pygame.Rect(rrect.x + 10, rrect.y + 28, 196, 13),
                    entry["rating"],
                    pal,
                    show_endpoints=False,
                )

            if st == "done":
                res_s = f"{entry['w']}W-{entry['d']}D-{entry['l']}L"
                tot_g = max(1, entry["w"] + entry["d"] + entry["l"])
                sc = (entry["w"] + 0.5 * entry["d"]) / tot_g
                rcol = WIN_COLOR if sc > 0.5 else (LOSS_COLOR if sc < 0.5 else DRAW_COLOR)
                draw_text(self.screen, res_s, (rrect.right - 92, rrect.y + 16), 13, rcol, bold=True)
            elif st == "playing":
                res_s = f"LIVE {entry['w']}-{entry['d']}-{entry['l']}"
                draw_text(self.screen, res_s, (rrect.right - 96, rrect.y + 16), 12, ACCENT, bold=True)
            elif st in ("pending", "skipped"):
                btn_r = pygame.Rect(rrect.right - 76, rrect.y + 11, 66, 26)
                hov = btn_r.collidepoint(self.mouse_pos)
                is_sk = (st == "skipped")
                bfill = LOSS_COLOR if is_sk else (PANEL_HOVER if hov else PANEL)
                btcol = (250, 250, 252) if is_sk else TEXT_COLOR
                pygame.draw.rect(self.screen, bfill, btn_r, border_radius=5)
                pygame.draw.rect(self.screen, ACCENT if hov else BORDER, btn_r, width=1, border_radius=5)
                blbl = "Unskip" if is_sk else "Skip"
                bs = _render_text(blbl, 12, btcol, True)
                self.screen.blit(bs, bs.get_rect(center=btn_r.center))
                self._running_skip_hitboxes.append((entry["index"], btn_r))
            else:
                draw_text(self.screen, "N/A", (rrect.right - 50, rrect.y + 16), 12, DIM_TEXT)

        if max_opp_scroll > 0:
            sb_x = opp_panel.right - 10
            sb_y = start_y
            sb_h = vis_rows * row_h - 6
            th_h = max(24, int(sb_h * vis_rows / max(1, len(entries))))
            th_y = sb_y + int((sb_h - th_h) * self.running_opp_scroll / max_opp_scroll)
            pygame.draw.rect(self.screen, BORDER, pygame.Rect(sb_x, sb_y, 4, sb_h), border_radius=2)
            pygame.draw.rect(self.screen, ACCENT, pygame.Rect(sb_x, th_y, 4, th_h), border_radius=2)

    def _copy_error_report(self):
        try:
            copied = _set_clipboard_text(self.error_report)
        except Exception:
            copied = False
        self.error_clipboard_status = (
            "Full error report copied to clipboard."
            if copied else "Clipboard unavailable. Use Copy report to retry; see the log path below.")

    def _draw_error_report(self):
        draw_text_centered(self.screen, "Engine Error",
                           (WINDOW_WIDTH // 2, 40), 30, ERROR_COLOR, bold=True)
        draw_text(self.screen, self.error_clipboard_status, (40, 85), 16, TEXT_COLOR)
        draw_text(self.screen, "Scroll to read details. Copy report includes the full failure history.",
                  (40, 113), 14, DIM_TEXT)
        rect = ERROR_REPORT_RECT
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=8)
        font = _get_font(_FONT_FAMILY, 14)
        if self._error_lines is None:
            self._error_lines = _wrap_error_text(self.error_report, font, rect.w - 24)
        line_height = max(20, font.get_linesize())
        visible = max(1, (rect.h - 20) // line_height)
        self.error_scroll = min(self.error_scroll, max(0, len(self._error_lines) - visible))
        for row, line in enumerate(self._error_lines[self.error_scroll:self.error_scroll + visible]):
            draw_text(self.screen, line, (rect.x + 12, rect.y + 10 + row * line_height),
                      14, TEXT_COLOR)
        self._draw_browse_button(ERROR_COPY_RECT, "Copy report", primary=True)
        self._draw_browse_button(ERROR_BACK_RECT, "Back to menu")

    def _draw_replay_view(self):
        g = self.replay_game
        if not g:
            return
        _ef = globals().get("ef")
        plies = g.get("plies", ())
        ply_idx = max(0, min(int(getattr(self, "replay_ply", 0)), len(plies)))
        fen = self._replay_current_fen()
        flipped = self._effective_replay_flipped()

        # Header
        self._draw_settings_button(self.replay_back_rect, "← Back to Results", primary=False)
        self._draw_settings_button(self.replay_flip_rect, "Flip Board (F)", active=flipped)
        title = (
            f"Game #{g.get('game_number', 1)}:  {g.get('target_name', 'Target')} "
            f"({'White' if g.get('target_is_white') else 'Black'})  vs  "
            f"{g.get('opponent_name', 'Opponent')} ({g.get('opponent_rating', 0)})   ·   {g.get('pgn_result', '')}"
        )
        draw_text(self.screen, title[:82], (322, 20), 17, ACCENT, bold=True)
        pygame.draw.line(self.screen, BORDER, (20, 58), (WINDOW_WIDTH - 20, 58), 1)

        # Stronger Stockfish Eval Bar
        rew = getattr(self, "replay_eval_worker", None)
        if rew is not None:
            rew.request_fen(fen)
            ev_cp, ev_mate, ev_depth = rew.get_eval(fen)
            badge = f"d{ev_depth}" if ev_depth > 0 else "EVAL"
        elif _ef is not None:
            ev_cp, ev_mate = _ef.evaluate_board_static_cp(_get_board(fen))
            ev_depth = 0
            badge = "EVAL"
        else:
            ev_cp, ev_mate, ev_depth, badge = 0, None, 0, "EVAL"

        bsize = 464
        bpos = (64, 112)
        self._draw_eval_bar(
            pygame.Rect(28, bpos[1], 26, bsize),
            ev_cp, ev_mate, flipped=flipped, badge=badge,
        )

        # Clocks at selected ply
        init_clk = 30.0
        if ply_idx == 0:
            w_left, b_left, mv_time, cur_ply_obj = init_clk, init_clk, 0.0, None
        else:
            cur_ply_obj = plies[ply_idx - 1]
            w_left = cur_ply_obj.get("white_left", init_clk)
            b_left = cur_ply_obj.get("black_left", init_clk)
            mv_time = cur_ply_obj.get("move_time", 0.0)

        for side_white, sy in ((bool(flipped), bpos[1] - 40), (not bool(flipped), bpos[1] + bsize + 8)):
            srect = pygame.Rect(bpos[0], sy, bsize, 32)
            pygame.draw.rect(self.screen, PANEL, srect, border_radius=7)
            pygame.draw.rect(self.screen, BORDER, srect, width=1, border_radius=7)
            is_t = (side_white == bool(g.get("target_is_white", True)))
            nm = g.get("target_name", "Target") if is_t else f"{g.get('opponent_name', 'Opponent')} ({g.get('opponent_rating', 0)})"
            draw_text(self.screen, nm[:36], (srect.x + 14, srect.y + 7),
                      14, ACCENT if is_t else TEXT_COLOR, bold=is_t)
            cval = w_left if side_white else b_left
            self._draw_clock_pill(
                pygame.Rect(srect.right - 90, srect.y + 3, 84, 26),
                cval,
                active=(cur_ply_obj is not None and cur_ply_obj.get("mover_is_white") == side_white),
            )

        last_mv = None
        if cur_ply_obj and len(cur_ply_obj.get("uci", "")) >= 4:
            try:
                last_mv = (
                    chess.parse_square(cur_ply_obj["uci"][:2]),
                    chess.parse_square(cur_ply_obj["uci"][2:4]),
                )
            except Exception:
                last_mv = None

        draw_board(
            self.screen, fen, bpos,
            last_move=last_mv,
            flipped=flipped,
            show_coords=not getattr(self, "cfg_hide_coords", False),
            board_size=bsize,
        )
        pygame.draw.rect(
            self.screen, BORDER,
            pygame.Rect(bpos[0] - 2, bpos[1] - 2, bsize + 4, bsize + 4), width=2,
        )

        # Navigation buttons below board
        nav_y = bpos[1] + bsize + 52
        self._replay_nav_rects = []
        nav_specs = [
            ("first", "|◀ Start", 96),
            ("prev",  "◀ Prev (A/←)", 128),
            ("next",  "Next (D/→) ▶", 128),
            ("last",  "End ▶|", 96),
        ]
        nx = bpos[0]
        for act, lbl, bw in nav_specs:
            nr = pygame.Rect(nx, nav_y, bw, 36)
            self._draw_settings_button(nr, lbl)
            self._replay_nav_rects.append((act, nr))
            nx += bw + 6
        draw_text(
            self.screen,
            "Use Left / Right arrows or A / D keys to step through moves",
            (bpos[0], nav_y + 46), 13, DIM_TEXT,
        )

        # Right telemetry & move list panels
        info_r = pygame.Rect(556, 72, 660, 220)
        draw_rounded_panel(self.screen, info_r)
        ix, iy = info_r.x + 18, info_r.y + 14
        draw_section(self.screen, "MOVE TIMING, CLOCKS & ANALYSIS", (ix, iy), width=info_r.w - 36)
        if cur_ply_obj is None:
            opening_s = g.get("opening_name") or "Standard starting position"
            draw_text(self.screen, f"Ply 0 / {len(plies)}  ·  {opening_s}",
                      (ix, iy + 28), 16, TEXT_COLOR, bold=True)
            draw_text(self.screen, f"Move time: —   ·   White time left: {w_left:.2f}s   ·   Black time left: {b_left:.2f}s",
                      (ix, iy + 58), 14, DIM_TEXT)
        else:
            mnum = (ply_idx + 1) // 2
            dots = "." if cur_ply_obj.get("mover_is_white") else "..."
            mover_lbl = "Target" if (cur_ply_obj.get("mover_is_white") == g.get("target_is_white")) else "Opponent"
            draw_text(
                self.screen,
                f"Move {mnum}{dots} {cur_ply_obj.get('san', '')}   ({mover_lbl})   ·   Ply {ply_idx} / {len(plies)}",
                (ix, iy + 28), 17, TEXT_COLOR, bold=True,
            )
            draw_text(
                self.screen,
                f"Time spent on move: {mv_time:.3f}s",
                (ix, iy + 58), 15, GOLD, bold=True,
            )
            draw_text(
                self.screen,
                f"White clock remaining: {w_left:.2f}s     ·     Black clock remaining: {b_left:.2f}s",
                (ix, iy + 84), 14, TEXT_COLOR,
            )
            qual = cur_ply_obj.get("quality")
            cpl = cur_ply_obj.get("cpl")
            acc = cur_ply_obj.get("accuracy")
            if qual is not None and cpl is not None:
                draw_text(
                    self.screen,
                    f"Move quality: {qual}  (CPL {cpl:.1f}  ·  Accuracy {acc:.1f}%)",
                    (ix, iy + 112), 14, ACCENT,
                )

        ev_lbl = _ef.format_eval_label(ev_cp, ev_mate) if _ef is not None else "0.0"
        src_lbl = (
            f"Stockfish Replay Analysis (depth {ev_depth})"
            if (rew is not None and rew.engine_ready and ev_depth > 0)
            else "Position Evaluation"
        )
        g_mq = g.get("move_quality")
        mq_txt = (
            f"   ·   Game Move-Quality Elo: {g_mq['move_quality_elo']:.0f} ({g_mq['accuracy_pct']:.1f}%)"
            if g_mq else ""
        )
        draw_text(self.screen, f"{src_lbl}: {ev_lbl}{mq_txt}",
                  (ix, iy + 144), 14, DIM_TEXT)
        draw_text(self.screen, f"Result: {g.get('pgn_result', '')}  ({g.get('termination', '')})",
                  (ix, iy + 170), 13, DIM_TEXT)

        # Clickable Move Sheet
        ml_rect = pygame.Rect(556, 306, 660, 444)
        draw_rounded_panel(self.screen, ml_rect)
        draw_text(self.screen, "MOVE LIST  (CLICK ANY MOVE OR PRESS ← / → / A / D)",
                  (ml_rect.x + 18, ml_rect.y + 14), 13, ACCENT, bold=True)
        pygame.draw.line(self.screen, BORDER,
                         (ml_rect.x + 16, ml_rect.y + 38),
                         (ml_rect.right - 16, ml_rect.y + 38), 1)
        self._replay_move_hitboxes = []
        full_rows = (len(plies) + 1) // 2
        vis_m = 14
        m_scroll = max(0, min(getattr(self, "replay_moves_scroll", 0), max(0, full_rows - vis_m)))
        self.replay_moves_scroll = m_scroll
        for r_i in range(vis_m):
            full_idx = m_scroll + r_i
            if full_idx >= full_rows:
                break
            ry = ml_rect.y + 46 + r_i * 27
            draw_text(self.screen, f"{full_idx + 1}.", (ml_rect.x + 18, ry + 4), 13, DIM_TEXT)
            for side_off, col_x in ((0, ml_rect.x + 64), (1, ml_rect.x + 356)):
                p_num = full_idx * 2 + side_off + 1
                if p_num > len(plies):
                    continue
                p_obj = plies[p_num - 1]
                cell = pygame.Rect(col_x, ry, 276, 24)
                sel = (p_num == ply_idx)
                hov = cell.collidepoint(self.mouse_pos)
                if sel or hov:
                    pygame.draw.rect(
                        self.screen, LIST_ROW_SEL if sel else PANEL_HOVER,
                        cell, border_radius=5,
                    )
                draw_text(
                    self.screen,
                    f"{p_obj.get('san', ''):<8}  ({p_obj.get('move_time', 0.0):.2f}s)",
                    (cell.x + 8, cell.y + 3), 13,
                    ACCENT if sel else TEXT_COLOR, bold=sel,
                )
                self._replay_move_hitboxes.append((p_num, cell))

    def draw_done(self):
        if self.error_text:
            self._draw_error_report()
            return
        elapsed = time.time() - self.done_start_time if self.done_start_time else 999.0
        if self.estimated_elo is not None and elapsed < REVEAL_DURATION:
            self._draw_mystery_reveal(elapsed)
            return
        if getattr(self, "replay_game", None) is not None and hasattr(self, "_draw_replay_view"):
            self._draw_replay_view()
            return

        if self.estimated_elo is None and not getattr(self, "playlist_results", None):
            draw_text_centered(self.screen, "Test Complete",
                               (WINDOW_WIDTH // 2, 40), 30, ACCENT, bold=True)
            draw_text_centered(self.screen, "Could not estimate Elo",
                               (WINDOW_WIDTH // 2, 100), 26, ERROR_COLOR)
            if hasattr(self, "_draw_settings_button"):
                self._draw_settings_button(self.done_back_rect, "← Back to Menu", primary=False)
            return

        if not self.confetti_spawned and self.estimated_elo is not None:
            self._spawn_confetti()
            self.confetti_spawned = True
            if self.celebration_sound:
                try:
                    self.celebration_sound.play()
                except Exception:
                    pass

        # Fallback path for bare AST-extracted HarnessApp in legacy tests
        if not hasattr(self, "_active_done_entry"):
            pop_elapsed = elapsed - REVEAL_DURATION
            draw_text_centered(self.screen, "Test Complete",
                               (WINDOW_WIDTH // 2, 30), 26, ACCENT, bold=True)
            self._draw_elo_pop(170, pop_elapsed)
            self._update_and_draw_confetti()
            return

        entry = self._active_done_entry()
        playlist_results = getattr(self, "playlist_results", ()) or ([entry] if entry else [])
        _ef = globals().get("ef")
        pal = self._current_palette()

        # Sticky top header bar
        pygame.draw.rect(self.screen, PANEL, pygame.Rect(0, 0, WINDOW_WIDTH, 58))
        pygame.draw.line(self.screen, BORDER, (0, 58), (WINDOW_WIDTH, 58), 1)
        self._draw_settings_button(self.done_back_rect, "← Back to Menu", primary=False)
        hdr_title = (
            f"Playlist Complete — {len(playlist_results)} Engines Tested"
            if len(playlist_results) > 1 else "Elo Calculation Complete"
        )
        draw_text_centered(self.screen, hdr_title, (WINDOW_WIDTH // 2, 29), 22, ACCENT, bold=True)
        self._draw_audio_controls(self.running_mute_rect, self.running_vol_rect)

        # Scrollable viewport below header
        vp = pygame.Rect(0, 59, WINDOW_WIDTH, WINDOW_HEIGHT - 59)
        rows = [
            (orig_idx, name, rating, ww, dd, ll)
            for orig_idx, (name, rating, ww, dd, ll) in enumerate(
                entry.get("per_opponent_results", ()) if entry else ()
            )
            if ww + dd + ll > 0
        ]
        games = entry.get("game_records", ()) if entry else ()

        # Compute virtual document height
        playlist_card_h = (74 + len(playlist_results) * 36) if len(playlist_results) > 1 else 0
        hero_h = 260
        opp_h = 84 + max(1, len(rows)) * 34
        games_h = 88 + max(1, len(games)) * 38
        content_h = 24 + playlist_card_h + hero_h + opp_h + games_h + 60
        self.done_max_scroll = max(0, content_h - vp.h)
        scroll_y = max(0, min(int(getattr(self, "done_scroll_y", 0)), self.done_max_scroll))
        self.done_scroll_y = scroll_y

        # Keep results_scroll clamped for backward test compatibility
        vis_legacy = globals().get("RESULTS_VISIBLE_ROWS", 13)
        self.results_scroll = max(0, min(getattr(self, "results_scroll", 0), max(0, len(rows) - vis_legacy)))

        old_clip = self.screen.get_clip()
        self.screen.set_clip(vp)
        cy_doc = vp.y + 18 - scroll_y

        # 1. Playlist All-Engines Leaderboard (when >1 engine tested)
        self._done_playlist_hitboxes = []
        if len(playlist_results) > 1:
            pl_card = pygame.Rect(40, cy_doc, WINDOW_WIDTH - 96, playlist_card_h - 14)
            draw_rounded_panel(self.screen, pl_card)
            draw_text(self.screen, "ALL TESTED ENGINES  (CLICK AN ENGINE TO VIEW DETAILS & GAMES)",
                      (pl_card.x + 20, pl_card.y + 14), 13, ACCENT, bold=True)
            ry = pl_card.y + 44
            for r_idx, res in enumerate(playlist_results):
                rrect = pygame.Rect(pl_card.x + 14, ry, pl_card.w - 28, 32)
                is_sel = (r_idx == getattr(self, "selected_result_idx", 0))
                hov = rrect.collidepoint(self.mouse_pos) and vp.collidepoint(self.mouse_pos)
                pygame.draw.rect(
                    self.screen,
                    LIST_ROW_SEL if is_sel else (PANEL_HOVER if hov else FIELD_BG),
                    rrect, border_radius=6,
                )
                pygame.draw.rect(self.screen, ACCENT if is_sel else BORDER, rrect, width=1, border_radius=6)
                e_elo = f"{res['estimated_elo']:.0f}" if res.get("estimated_elo") is not None else "ERR"
                mq_s = (
                    f"Move Elo {res['move_quality']['move_quality_elo']:.0f} ({res['move_quality']['accuracy_pct']:.1f}%)"
                    if res.get("move_quality") else "Move Elo —"
                )
                draw_text(self.screen, f"#{r_idx + 1}  {res.get('engine_name', 'Engine')}",
                          (rrect.x + 12, rrect.y + 7), 14, TEXT_COLOR, bold=is_sel)
                draw_text(self.screen, f"Match Elo: {e_elo}",
                          (rrect.x + 360, rrect.y + 7), 14, GOLD, bold=True)
                draw_text(self.screen, mq_s,
                          (rrect.x + 540, rrect.y + 7), 13, ACCENT)
                draw_text(
                    self.screen,
                    f"{res.get('wins', 0)}W - {res.get('draws', 0)}D - {res.get('losses', 0)}L",
                    (rrect.right - 160, rrect.y + 7), 13, DIM_TEXT,
                )
                self._done_playlist_hitboxes.append((r_idx, rrect))
                ry += 35
            cy_doc += playlist_card_h

        # 2. Hero Elo & Move-Quality Card
        hero_rect = pygame.Rect(40, cy_doc, WINDOW_WIDTH - 96, hero_h - 16)
        draw_rounded_panel(self.screen, hero_rect)
        pop_elapsed = max(0.0, elapsed - REVEAL_DURATION)
        if self.estimated_elo is not None:
            self._draw_elo_pop(hero_rect.y + 104, pop_elapsed, cx=hero_rect.x + 220)
            if _ef is not None:
                _ef.draw_elo_scale_bar(
                    self.screen,
                    pygame.Rect(hero_rect.x + 48, hero_rect.bottom - 42, 344, 16),
                    self.estimated_elo,
                    pal,
                    show_endpoints=True,
                    font_getter=lambda sz, bold=False: _get_font(_FONT_FAMILY, sz, bold=bold),
                )

        if entry:
            rx = hero_rect.x + 450
            ry = hero_rect.y + 22
            draw_text(self.screen, f"Engine: {entry.get('engine_name', 'Target')}",
                      (rx, ry), 20, TEXT_COLOR, bold=True)
            gp = entry.get("games_played", 0)
            ww, dd, ll = entry.get("wins", 0), entry.get("draws", 0), entry.get("losses", 0)
            sc = (ww + 0.5 * dd) / gp if gp else 0.0
            draw_text(
                self.screen,
                f"Games: {gp}    ·    W {ww}   D {dd}   L {ll}    ·    Score {sc:.1%}",
                (rx, ry + 32), 15, DIM_TEXT,
            )
            cfg_line = f"Config: {entry.get('target_config_str', '')}"
            if entry.get("high_elo_extended"):
                cfg_line += "   ·   3600+ Extended"
            draw_text(self.screen, cfg_line, (rx, ry + 56), 13, DIM_TEXT)

            mq = entry.get("move_quality")
            if mq:
                mq_box = pygame.Rect(rx, ry + 86, 320, 74)
                pygame.draw.rect(self.screen, FIELD_BG, mq_box, border_radius=10)
                pygame.draw.rect(self.screen, ACCENT, mq_box, width=1, border_radius=10)
                draw_text(self.screen, "MOVE-QUALITY ELO (PER-GAME AVG)",
                          (mq_box.x + 14, mq_box.y + 10), 11, ACCENT, bold=True)
                draw_text(self.screen, f"{mq['move_quality_elo']:.0f} Elo",
                          (mq_box.x + 14, mq_box.y + 28), 24, GOLD, bold=True)
                draw_text(self.screen, f"{mq['accuracy_pct']:.1f}% acc  ·  {mq['acpl']:.1f} ACPL",
                          (mq_box.x + 150, mq_box.y + 36), 13, TEXT_COLOR)

            rs = entry.get("resource_summary")
            if rs and rs.get("samples", 0) > 0:
                rs_box = pygame.Rect(rx + 336, ry + 86, 330, 74)
                pygame.draw.rect(self.screen, FIELD_BG, rs_box, border_radius=10)
                pygame.draw.rect(self.screen, BORDER, rs_box, width=1, border_radius=10)
                draw_text(self.screen, "ENGINE DATA TRACKING",
                          (rs_box.x + 14, rs_box.y + 10), 11, ACCENT, bold=True)
                draw_text(
                    self.screen,
                    f"CPU Avg {rs['avg_cpu_pct']:.1f}%  (Peak {rs['peak_cpu_pct']:.0f}%)",
                    (rs_box.x + 14, rs_box.y + 30), 13, TEXT_COLOR,
                )
                draw_text(
                    self.screen,
                    f"RAM Avg {rs['avg_ram_mb']:.1f} MB  (Peak {rs['peak_ram_mb']:.1f} MB)",
                    (rs_box.x + 14, rs_box.y + 50), 13, DIM_TEXT,
                )
        cy_doc += hero_h

        # 3. Per-Opponent Breakdown Card (with 300–4010 Elo scale bar + arrow!)
        opp_card = pygame.Rect(40, cy_doc, WINDOW_WIDTH - 96, opp_h - 16)
        draw_rounded_panel(self.screen, opp_card)
        draw_text(self.screen, "PER-OPPONENT RESULTS",
                  (opp_card.x + 20, opp_card.y + 14), 14, ACCENT, bold=True)
        col_x = [opp_card.x + 20, opp_card.x + 390, opp_card.x + 480,
                 opp_card.x + 710, opp_card.x + 780, opp_card.x + 850, opp_card.x + 940]
        for cx_h, h_txt, h_col in zip(
            col_x,
            ["Opponent", "Rating", "Scale (300–4010)", "W", "D", "L", "Score"],
            [ACCENT, ACCENT, ACCENT, WIN_COLOR, DRAW_COLOR, LOSS_COLOR, ACCENT],
        ):
            draw_text(self.screen, h_txt, (cx_h, opp_card.y + 42), 13, h_col, bold=True)

        ext_start = entry.get("extension_start_index") if entry else None
        ry = opp_card.y + 68
        for r_i, (orig_idx, name, rating, ww, dd, ll) in enumerate(rows):
            if r_i % 2 == 0:
                pygame.draw.rect(
                    self.screen, FIELD_BG,
                    pygame.Rect(opp_card.x + 12, ry - 3, opp_card.w - 24, 30),
                    border_radius=5,
                )
            tot = max(1, ww + dd + ll)
            pct = (ww + 0.5 * dd) / tot * 100.0
            frac = (ww + 0.5 * dd) / tot
            is_ext = ext_start is not None and orig_idx >= ext_start
            draw_text(self.screen, name[:40], (col_x[0], ry + 3), 14, TEXT_COLOR)
            draw_text(self.screen, f"{rating}", (col_x[1], ry + 3), 14,
                      GOLD if is_ext else TEXT_COLOR, bold=is_ext)
            if _ef is not None:
                _ef.draw_elo_scale_bar(
                    self.screen,
                    pygame.Rect(col_x[2], ry + 6, 190, 14),
                    rating, pal, show_endpoints=False,
                )
            draw_text(self.screen, str(ww), (col_x[3], ry + 3), 14, WIN_COLOR)
            draw_text(self.screen, str(dd), (col_x[4], ry + 3), 14, DRAW_COLOR)
            draw_text(self.screen, str(ll), (col_x[5], ry + 3), 14, LOSS_COLOR)
            sc_col = WIN_COLOR if frac > 0.55 else (LOSS_COLOR if frac < 0.45 else DRAW_COLOR)
            draw_text(self.screen, f"{pct:5.1f}%", (col_x[6], ry + 3), 14, sc_col, bold=True)
            ry += 34
        cy_doc += opp_h

        # 4. Individual Games Replay List
        self._done_game_hitboxes = []
        gm_card = pygame.Rect(40, cy_doc, WINDOW_WIDTH - 96, games_h - 16)
        draw_rounded_panel(self.screen, gm_card)
        draw_text(
            self.screen,
            "PLAYED GAMES  —  CLICK ANY GAME TO NAVIGATE MOVES (← / → OR A / D) WITH STRONG STOCKFISH EVAL",
            (gm_card.x + 20, gm_card.y + 14), 13, ACCENT, bold=True,
        )
        pygame.draw.line(self.screen, BORDER,
                         (gm_card.x + 16, gm_card.y + 40),
                         (gm_card.right - 16, gm_card.y + 40), 1)
        gy = gm_card.y + 50
        if not games:
            draw_text(self.screen, "No recorded move histories available.",
                      (gm_card.x + 20, gy + 6), 14, DIM_TEXT)
        for g_rec in games:
            grect = pygame.Rect(gm_card.x + 14, gy, gm_card.w - 28, 34)
            hov = grect.collidepoint(self.mouse_pos) and vp.collidepoint(self.mouse_pos)
            pygame.draw.rect(
                self.screen, PANEL_HOVER if hov else FIELD_BG, grect, border_radius=6
            )
            pygame.draw.rect(
                self.screen, ACCENT if hov else BORDER, grect, width=1, border_radius=6
            )
            res_c = g_rec.get("result", "D")
            rcol = WIN_COLOR if res_c == "W" else (LOSS_COLOR if res_c == "L" else DRAW_COLOR)
            col_tag = "White" if g_rec.get("target_is_white") else "Black"
            n_plies = len(g_rec.get("plies", ()))
            g_mq = g_rec.get("move_quality")
            mq_str = (
                f"Move Elo {g_mq['move_quality_elo']:.0f} ({g_mq['accuracy_pct']:.1f}%)"
                if g_mq else "Move Elo —"
            )
            draw_text(
                self.screen,
                f"Game #{g_rec.get('game_number', 1):<3}  ({col_tag})  vs  {g_rec.get('opponent_name', 'Opponent')[:28]} ({g_rec.get('opponent_rating', 0)})",
                (grect.x + 12, grect.y + 8), 13, TEXT_COLOR, bold=hov,
            )
            draw_text(
                self.screen,
                f"{res_c}  {g_rec.get('pgn_result', '')}  ({n_plies} plies)",
                (grect.x + 520, grect.y + 8), 13, rcol, bold=True,
            )
            draw_text(self.screen, mq_str, (grect.x + 710, grect.y + 8), 13, GOLD)
            draw_text(self.screen, "Replay Moves →",
                      (grect.right - 138, grect.y + 8), 13, ACCENT, bold=True)
            self._done_game_hitboxes.append((g_rec, grect))
            gy += 38

        self.screen.set_clip(old_clip)

        # Page scrollbar
        if self.done_max_scroll > 0:
            sb_x = WINDOW_WIDTH - 16
            sb_y = vp.y + 8
            sb_h = vp.h - 16
            th_h = max(32, int(sb_h * vp.h / max(1, content_h)))
            th_y = sb_y + int((sb_h - th_h) * scroll_y / self.done_max_scroll)
            pygame.draw.rect(self.screen, BORDER, pygame.Rect(sb_x, sb_y, 6, sb_h), border_radius=3)
            pygame.draw.rect(self.screen, ACCENT, pygame.Rect(sb_x, th_y, 6, th_h), border_radius=3)

        self._update_and_draw_confetti()

    def reset(self):
        if self.worker and self.worker.is_alive():
            if hasattr(self.worker, "stop"):
                self.worker.stop()
            else:
                self.worker.running = False
            self.worker.join(timeout=1.5)
        if hasattr(self, "_stop_aux_workers"):
            self._stop_aux_workers()
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        try:
            pygame.key.set_repeat()
        except Exception:
            pass
        self.state = "MENU"
        if getattr(self, "engine_playlist", None):
            self.target_path = self.engine_playlist[0]
            self.status_text = f"Playlist ready ({len(self.engine_playlist)} queued)."
        else:
            self.target_path = None
            self.status_text = "Select a UCI engine to begin."
        self.estimated_elo = None
        self.estimate_kind = None
        self.confidence = None
        self.error_text = None
        self.error_report = ""
        self.error_clipboard_status = ""
        self.error_scroll = 0
        self.results_scroll = 0
        self.done_scroll_y = 0
        self.done_max_scroll = 0
        self.confirm_back_to_menu = False
        self.replay_game = None
        self.replay_flipped = None
        self._error_lines = None
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
        self.dragging_rgb_slider = None
        self.dragging_audio_volume = False
        self.settings_snapshot = None
        self.browse_show_hidden = False
        self.browse_hidden_count = 0
        self._keys_down = set()

    def shutdown(self):
        if self.worker and self.worker.is_alive():
            if hasattr(self.worker, "stop"):
                self.worker.stop()
            else:
                self.worker.running = False
            self.worker.join(timeout=2)
        if hasattr(self, "_stop_aux_workers"):
            self._stop_aux_workers()
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