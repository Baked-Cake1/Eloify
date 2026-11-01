"""Clipboard and browse shortcuts, without initializing the pygame GUI.

Win32 calls are mocked so pointer declarations and ownership can be checked on
Linux too. Real desktop clipboard integration still needs a Windows/macOS run.
"""
import ast
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pygame

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / "main.py").read_text())
ns = dict(os=os, sys=SimpleNamespace(platform="win32"),
          subprocess=subprocess, pygame=pygame)
names = {"_windows_clipboard_api", "_get_clipboard_text", "_set_clipboard_text", "TextField"}
nodes = [n for n in tree.body
         if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
app = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EloifyApp")
nodes.append(ast.ClassDef(
    name="BrowseApp", bases=[], keywords=[], decorator_list=[],
    body=[n for n in app.body if isinstance(n, ast.FunctionDef) and n.name in {
        "_handle_browse_key_down", "handle_key_up", "handle_focus_lost", "_open_browse_dialog"}]))
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
             "main.py", "exec"), ns)


class WindowsClipboardTests(unittest.TestCase):
    def setUp(self):
        ns["sys"].platform = "win32"
        self.handle = 0x123456789
        self.pointer = 0x23456789A
        self.user = SimpleNamespace(**{name: Mock(return_value=1) for name in (
            "OpenClipboard", "CloseClipboard", "EmptyClipboard", "GetClipboardData", "SetClipboardData")})
        self.kernel = SimpleNamespace(**{name: Mock(return_value=1) for name in (
            "GlobalAlloc", "GlobalLock", "GlobalUnlock", "GlobalFree")})
        self.user.GetClipboardData.return_value = self.handle
        self.user.SetClipboardData.return_value = self.handle
        self.kernel.GlobalAlloc.return_value = self.handle
        self.kernel.GlobalLock.return_value = self.pointer
        patcher = patch.object(ctypes, "windll", SimpleNamespace(
            user32=self.user, kernel32=self.kernel), create=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(pygame.display, "get_wm_info", return_value={"window": 0x3456789AB})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_read_unicode_with_pointer_sized_signatures(self):
        text = "C:\\引擎\\Échecs ♞.exe"
        with patch.object(ctypes, "wstring_at", return_value=text) as read:
            self.assertEqual(ns["_get_clipboard_text"](), text)
        read.assert_called_once_with(self.pointer)
        self.assertIs(self.user.GetClipboardData.restype, wintypes.HANDLE)
        self.assertIs(self.kernel.GlobalLock.restype, ctypes.c_void_p)
        self.assertEqual(self.kernel.GlobalLock.argtypes, [wintypes.HGLOBAL])
        self.kernel.GlobalUnlock.assert_called_once_with(self.handle)
        self.user.CloseClipboard.assert_called_once()

    def test_write_unicode_uses_window_owner_and_transfers_memory(self):
        text = "C:\\引擎\\Stockfish ♞.exe"
        with patch.object(ctypes, "memmove") as copy:
            self.assertTrue(ns["_set_clipboard_text"](text))
        data = text.encode("utf-16-le") + b"\0\0"
        self.user.OpenClipboard.assert_called_once_with(0x3456789AB)
        self.kernel.GlobalAlloc.assert_called_once_with(2, len(data))
        copy.assert_called_once_with(self.pointer, data, len(data))
        self.user.SetClipboardData.assert_called_once_with(13, self.handle)
        self.assertEqual(self.user.SetClipboardData.argtypes, [wintypes.UINT, wintypes.HANDLE])
        self.assertIs(self.user.SetClipboardData.restype, wintypes.HANDLE)
        self.assertEqual(self.kernel.GlobalAlloc.argtypes, [wintypes.UINT, ctypes.c_size_t])
        self.kernel.GlobalFree.assert_not_called()
        self.user.CloseClipboard.assert_called_once()

    def test_failed_write_frees_memory_and_reports_failure(self):
        for function in (self.kernel.GlobalLock, self.user.EmptyClipboard, self.user.SetClipboardData):
            with self.subTest(function=function):
                for mock in vars(self.kernel).values():
                    mock.reset_mock()
                function.return_value = 0
                with patch.object(ctypes, "memmove"):
                    self.assertFalse(ns["_set_clipboard_text"]("path"))
                self.kernel.GlobalFree.assert_called_once_with(self.handle)
                function.return_value = 1

    def test_busy_clipboard_does_not_allocate_or_empty(self):
        self.user.OpenClipboard.return_value = 0
        self.assertFalse(ns["_set_clipboard_text"]("path"))
        self.kernel.GlobalAlloc.assert_not_called()
        self.user.EmptyClipboard.assert_not_called()
        self.user.CloseClipboard.assert_not_called()

    def test_read_exception_unlocks_and_closes(self):
        with patch.object(ctypes, "wstring_at", side_effect=RuntimeError("read failed")), \
                patch.object(subprocess, "check_output", return_value=b"fallback"):
            self.assertEqual(ns["_get_clipboard_text"](), "fallback")
        self.kernel.GlobalUnlock.assert_called_once_with(self.handle)
        self.user.CloseClipboard.assert_called_once()


class DesktopFallbackTests(unittest.TestCase):
    def setUp(self):
        ns["sys"].platform = "linux"

    def test_wayland_unicode_read(self):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}), \
                patch.object(subprocess, "check_output", return_value="引擎.exe".encode()) as read:
            self.assertEqual(ns["_get_clipboard_text"](), "引擎.exe")
        self.assertEqual(read.call_args.args[0][0], "wl-paste")
        self.assertEqual(read.call_args.kwargs["timeout"], 2)

    def test_failed_write_command_tries_next_backend(self):
        with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}), \
                patch.object(subprocess, "run", side_effect=[
                    subprocess.CalledProcessError(1, "wl-copy"), SimpleNamespace(returncode=0)]) as write:
            self.assertTrue(ns["_set_clipboard_text"]("引擎.exe"))
        self.assertEqual(write.call_count, 2)
        self.assertTrue(write.call_args.kwargs["check"])
        self.assertEqual(write.call_args.kwargs["timeout"], 2)

    def test_sdl_read_without_external_utilities(self):
        with patch.object(subprocess, "check_output", side_effect=FileNotFoundError), \
                patch.object(pygame.scrap, "get_init", return_value=True), \
                patch.object(pygame.scrap, "set_mode"), \
                patch.object(pygame.scrap, "get", return_value="é.exe\0".encode()):
            self.assertEqual(ns["_get_clipboard_text"](), "é.exe")

    def test_failed_backends_report_false(self):
        with patch.object(subprocess, "run", side_effect=FileNotFoundError), \
                patch.object(pygame.scrap, "get_init", return_value=True), \
                patch.object(pygame.scrap, "set_mode", side_effect=RuntimeError("no display")):
            self.assertFalse(ns["_set_clipboard_text"]("path"))


class BrowseShortcutTests(unittest.TestCase):
    def setUp(self):
        ns["sys"].platform = "win32"
        self.app = ns["BrowseApp"]()
        self.app.state = "BROWSE_ENGINE"
        self.app._keys_down = set()
        self.app.browse_path_field = ns["TextField"]("old path")
        self.app.browse_path_field.select_all()
        self.app.browse_focus = "text"
        self.app.browse_selected = 3
        self.app.browse_drag_active = False
        self.app.browse_error = ""

    def key(self, key, mods=pygame.KMOD_CTRL):
        self.app._handle_browse_key_down(SimpleNamespace(key=key, mod=mods, unicode=""))

    def test_paste_replaces_selection_and_deselects_old_file(self):
        self.app.browse_focus = "list"
        with patch.dict(ns, _get_clipboard_text=lambda: '\r\n"C:\\引擎\\Stockfish.exe"\r\n'):
            self.key(pygame.K_v)
        self.assertEqual(self.app.browse_path_field.text, "C:\\引擎\\Stockfish.exe")
        self.assertEqual(self.app.browse_selected, -1)
        self.assertEqual(self.app.browse_focus, "text")

    def test_copy_preserves_unicode_selection(self):
        copy = Mock(return_value=True)
        self.app.browse_path_field.set_text("引擎.exe")
        self.app.browse_path_field.select_all()
        with patch.dict(ns, _set_clipboard_text=copy):
            self.key(pygame.K_c)
        copy.assert_called_once_with("引擎.exe")
        self.assertEqual(self.app.browse_path_field.text, "引擎.exe")

    def test_failed_cut_keeps_selected_text(self):
        with patch.dict(ns, _set_clipboard_text=lambda text: False):
            self.key(pygame.K_x)
        self.assertEqual(self.app.browse_path_field.text, "old path")
        self.assertTrue(self.app.browse_path_field.has_selection())
        self.assertIn("not cut", self.app.browse_error)

    def test_successful_cut_deletes_selection(self):
        with patch.dict(ns, _set_clipboard_text=lambda text: True):
            self.key(pygame.K_x)
        self.assertEqual(self.app.browse_path_field.text, "")
        self.assertEqual(self.app.browse_selected, -1)

    def test_command_v_on_macos_does_not_insert_literal_v(self):
        ns["sys"].platform = "darwin"
        with patch.dict(ns, _get_clipboard_text=lambda: "/Users/é/engine"):
            self.key(pygame.K_v, pygame.KMOD_GUI)
        self.assertEqual(self.app.browse_path_field.text, "/Users/é/engine")

    def test_focus_loss_unblocks_next_paste_without_keyup(self):
        with patch.dict(ns, _get_clipboard_text=lambda: "abc"):
            self.key(pygame.K_v)
            self.key(pygame.K_v)  # Auto-repeat should not paste twice.
            self.assertEqual(self.app.browse_path_field.text, "abc")
            self.app.browse_drag_active = True
            self.app.handle_focus_lost()
            self.assertFalse(self.app.browse_drag_active)
            self.key(pygame.K_v)
        self.assertEqual(self.app.browse_path_field.text, "abcabc")

    def test_open_selects_initial_directory_for_path_paste(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(os.path, "expanduser", return_value=folder), \
                patch.object(pygame.key, "set_repeat"):
            self.app.target_path = None
            self.app._refresh_dir_listing = Mock()
            self.app._open_browse_dialog()
        field = self.app.browse_path_field
        self.assertEqual(field.get_selection_range(), (0, len(folder)))


if __name__ == "__main__":
    unittest.main()
