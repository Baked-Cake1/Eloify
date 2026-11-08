"""Tests for hiding/showing hidden folders and files in the Browse Engine dialog."""
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import main as eloify


def _make_fake_direntry(name, path, is_dir=False, file_attributes=0, flags=0, stat_error=None):
    st = SimpleNamespace(st_file_attributes=file_attributes, st_flags=flags)

    class FakeDirEntry:
        def __init__(self):
            self.name = name
            self.path = path

        def is_dir(self, follow_symlinks=True):
            return is_dir

        def stat(self, follow_symlinks=True):
            if stat_error is not None:
                raise stat_error
            return st

    return FakeDirEntry()


class HiddenEntryDetectionTests(unittest.TestCase):
    def test_dotfiles_and_dotfolders_are_hidden_except_dot_and_dotdot(self):
        self.assertTrue(eloify._is_hidden_entry(_make_fake_direntry(".git", "/tmp/.git", is_dir=True)))
        self.assertTrue(eloify._is_hidden_entry(_make_fake_direntry(".stockfish", "/tmp/.stockfish", is_dir=False)))
        self.assertFalse(eloify._is_hidden_entry(_make_fake_direntry(".", "/tmp/.", is_dir=True)))
        self.assertFalse(eloify._is_hidden_entry(_make_fake_direntry("..", "/tmp/..", is_dir=True)))
        self.assertFalse(eloify._is_hidden_entry(_make_fake_direntry("engines", "/tmp/engines", is_dir=True)))
        self.assertFalse(eloify._is_hidden_entry(_make_fake_direntry("stockfish", "/tmp/stockfish", is_dir=False)))

    def test_windows_file_attribute_hidden_is_detected(self):
        hidden_win = _make_fake_direntry(
            "AppData",
            r"C:\Users\Player\AppData",
            is_dir=True,
            file_attributes=eloify.FILE_ATTRIBUTE_HIDDEN | 0x10,
        )
        normal_win = _make_fake_direntry(
            "Engines",
            r"C:\Users\Player\Engines",
            is_dir=True,
            file_attributes=0x10,  # FILE_ATTRIBUTE_DIRECTORY only
        )
        self.assertTrue(eloify._is_hidden_entry(hidden_win))
        self.assertFalse(eloify._is_hidden_entry(normal_win))

    def test_macos_uf_hidden_flag_is_detected(self):
        hidden_mac = _make_fake_direntry(
            "Library",
            "/Users/player/Library",
            is_dir=True,
            flags=eloify.UF_HIDDEN,
        )
        normal_mac = _make_fake_direntry(
            "Engines",
            "/Users/player/Engines",
            is_dir=True,
            flags=0,
        )
        self.assertTrue(eloify._is_hidden_entry(hidden_mac))
        self.assertFalse(eloify._is_hidden_entry(normal_mac))

    def test_stat_oserror_falls_back_cleanly(self):
        broken_normal = _make_fake_direntry(
            "dangling_link",
            "/tmp/dangling_link",
            stat_error=FileNotFoundError("broken symlink"),
        )
        broken_dot = _make_fake_direntry(
            ".dangling_hidden",
            "/tmp/.dangling_hidden",
            stat_error=FileNotFoundError("broken symlink"),
        )
        self.assertFalse(eloify._is_hidden_entry(broken_normal))
        self.assertTrue(eloify._is_hidden_entry(broken_dot))


class BrowseDialogHiddenFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _make_headless_app(self):
        app = eloify.EloifyApp.__new__(eloify.EloifyApp)
        app.screen = pygame.Surface((eloify.WINDOW_WIDTH, eloify.WINDOW_HEIGHT))
        app.state = "MENU"
        app.target_path = None
        app.status_text = "Select a UCI engine to begin."
        app.mouse_pos = (0, 0)
        app._keys_down = set()
        app.browse_cwd = ""
        app.browse_entries = []
        app.browse_selected = -1
        app.browse_scroll = 0
        app.browse_show_hidden = False
        app.browse_hidden_count = 0
        app.browse_error = ""
        app.browse_path_field = eloify.TextField("")
        app.browse_focus = "text"
        app.browse_drag_active = False
        app._last_browse_click_time = 0.0
        app._last_browse_click_idx = -1
        return app

    def test_checkbox_label_and_toolbar_layout_do_not_overlap(self):
        self.assertEqual(eloify.BROWSE_SHOW_HIDDEN_LABEL, "Show hidden folders/files")
        self.assertTrue(eloify.BROWSE_PANEL.contains(eloify.BROWSE_SHOW_HIDDEN_RECT))
        self.assertEqual(eloify.BROWSE_SHOW_HIDDEN_RECT.y, eloify.BROWSE_UP_RECT.y)
        self.assertEqual(eloify.BROWSE_SHOW_HIDDEN_RECT.h, eloify.BROWSE_UP_RECT.h)
        self.assertEqual(eloify.BROWSE_SHOW_HIDDEN_RECT.right, eloify.BROWSE_LIST.right)
        for other in (
            eloify.BROWSE_FIELD,
            eloify.BROWSE_UP_RECT,
            eloify.BROWSE_HOME_RECT,
            eloify.BROWSE_REFRESH_RECT,
            eloify.BROWSE_LIST,
        ):
            self.assertFalse(
                eloify.BROWSE_SHOW_HIDDEN_RECT.colliderect(other),
                f"Checkbox rect overlaps {other}",
            )

    def test_hidden_folders_and_files_are_hidden_by_default_and_shown_when_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "visible_dir").mkdir()
            (root / ".hidden_dir").mkdir()
            (root / "stockfish").write_text("", encoding="utf-8")
            (root / ".secret_engine").write_text("", encoding="utf-8")

            app = self._make_headless_app()
            with patch.object(os.path, "expanduser", return_value=str(root)):
                app._open_browse_dialog()

            self.assertFalse(app.browse_show_hidden)
            self.assertEqual(app.browse_hidden_count, 2)
            names_default = [e[0] for e in app.browse_entries]
            self.assertIn("..", names_default)
            self.assertIn("visible_dir", names_default)
            self.assertIn("stockfish", names_default)
            self.assertNotIn(".hidden_dir", names_default)
            self.assertNotIn(".secret_engine", names_default)

            # Click the 'Show hidden folders/files' checkbox
            app._handle_browse_click(eloify.BROWSE_SHOW_HIDDEN_RECT.center)
            self.assertTrue(app.browse_show_hidden)
            self.assertEqual(app.browse_hidden_count, 0)
            names_checked = [e[0] for e in app.browse_entries]
            self.assertEqual(
                names_checked,
                ["..", ".hidden_dir", "visible_dir", ".secret_engine", "stockfish"],
            )

            # Click again to untick
            app._handle_browse_click(eloify.BROWSE_SHOW_HIDDEN_RECT.center)
            self.assertFalse(app.browse_show_hidden)
            self.assertEqual(app.browse_hidden_count, 2)
            self.assertEqual(
                [e[0] for e in app.browse_entries],
                ["..", "visible_dir", "stockfish"],
            )

    def test_toggling_checkbox_preserves_visible_selection_and_clears_hidden_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".alpha_hidden").write_text("", encoding="utf-8")
            visible_engine = root / "stockfish"
            visible_engine.write_text("", encoding="utf-8")

            app = self._make_headless_app()
            with patch.object(os.path, "expanduser", return_value=str(root)):
                app._open_browse_dialog()

            # Select visible 'stockfish' while hidden files are hidden
            sf_idx = [e[0] for e in app.browse_entries].index("stockfish")
            app.browse_selected = sf_idx

            # Ticking 'Show hidden folders/files' inserts '.alpha_hidden' before 'stockfish'
            # and keeps 'stockfish' selected at its new index.
            app._handle_browse_click(eloify.BROWSE_SHOW_HIDDEN_RECT.center)
            self.assertTrue(app.browse_show_hidden)
            self.assertGreaterEqual(app.browse_selected, 0)
            self.assertEqual(
                os.path.normpath(app.browse_entries[app.browse_selected][2]),
                os.path.normpath(str(visible_engine)),
            )

            # Select '.alpha_hidden', then untick checkbox -> selection must clear to -1
            hidden_idx = [e[0] for e in app.browse_entries].index(".alpha_hidden")
            app.browse_selected = hidden_idx
            app._handle_browse_click(eloify.BROWSE_SHOW_HIDDEN_RECT.center)
            self.assertFalse(app.browse_show_hidden)
            self.assertEqual(app.browse_selected, -1)

    def test_windows_hidden_attribute_entries_filtered_until_checked(self):
        app = self._make_headless_app()
        app.browse_cwd = r"C:\Engines"
        fake_entries = [
            _make_fake_direntry("AppData", r"C:\Engines\AppData", is_dir=True,
                                file_attributes=eloify.FILE_ATTRIBUTE_HIDDEN | 0x10),
            _make_fake_direntry("OpenBench", r"C:\Engines\OpenBench", is_dir=True,
                                file_attributes=0x10),
            _make_fake_direntry("helper.dll", r"C:\Engines\helper.dll", is_dir=False,
                                file_attributes=eloify.FILE_ATTRIBUTE_HIDDEN),
            _make_fake_direntry("stockfish.exe", r"C:\Engines\stockfish.exe", is_dir=False,
                                file_attributes=0x20),
        ]
        with patch.object(os, "scandir", return_value=fake_entries):
            app._refresh_dir_listing()
            self.assertEqual([e[0] for e in app.browse_entries if e[0] != ".."],
                             ["OpenBench", "stockfish.exe"])
            self.assertEqual(app.browse_hidden_count, 2)

            app._toggle_browse_show_hidden()
            self.assertTrue(app.browse_show_hidden)
            self.assertEqual(
                [e[0] for e in app.browse_entries if e[0] != ".."],
                ["AppData", "OpenBench", "helper.dll", "stockfish.exe"],
            )

    def test_navigation_preserves_checkbox_state_and_reset_clears_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / "sub"
            sub.mkdir()
            (sub / ".hidden_in_sub").write_text("", encoding="utf-8")
            (sub / "visible_in_sub").write_text("", encoding="utf-8")

            app = self._make_headless_app()
            with patch.object(os.path, "expanduser", return_value=str(root)):
                app._open_browse_dialog()

            app._handle_browse_click(eloify.BROWSE_SHOW_HIDDEN_RECT.center)
            self.assertTrue(app.browse_show_hidden)

            app._browse_goto(str(sub))
            self.assertTrue(app.browse_show_hidden)
            self.assertIn(".hidden_in_sub", [e[0] for e in app.browse_entries])

            app.worker = None
            app.reset()
            self.assertFalse(app.browse_show_hidden)
            self.assertEqual(app.browse_hidden_count, 0)

    def test_keyboard_shortcuts_toggle_hidden_checkbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".secret").write_text("", encoding="utf-8")
            app = self._make_headless_app()
            with patch.object(os.path, "expanduser", return_value=str(root)):
                app._open_browse_dialog()

            with patch.object(eloify.sys, "platform", "linux"):
                ev = SimpleNamespace(key=pygame.K_h, mod=pygame.KMOD_CTRL, unicode="")
                app._handle_browse_key_down(ev)
                self.assertTrue(app.browse_show_hidden)

            app._keys_down.clear()
            with patch.object(eloify.sys, "platform", "darwin"):
                ev = SimpleNamespace(
                    key=pygame.K_PERIOD,
                    mod=pygame.KMOD_GUI | pygame.KMOD_SHIFT,
                    unicode=".",
                )
                app._handle_browse_key_down(ev)
                self.assertFalse(app.browse_show_hidden)

    def test_draw_browse_overlay_renders_unchecked_and_checked_without_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".hidden_engine").write_text("", encoding="utf-8")
            (root / "stockfish").write_text("", encoding="utf-8")

            app = self._make_headless_app()
            with patch.object(os.path, "expanduser", return_value=str(root)):
                app._open_browse_dialog()

            app.draw_browse_overlay()
            unchecked_pixels = pygame.image.tostring(
                app.screen.subsurface(eloify.BROWSE_SHOW_HIDDEN_RECT), "RGB"
            )

            app._toggle_browse_show_hidden()
            app.draw_browse_overlay()
            checked_pixels = pygame.image.tostring(
                app.screen.subsurface(eloify.BROWSE_SHOW_HIDDEN_RECT), "RGB"
            )

            self.assertNotEqual(unchecked_pixels, checked_pixels)


if __name__ == "__main__":
    unittest.main()
