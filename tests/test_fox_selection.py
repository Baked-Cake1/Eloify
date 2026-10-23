"""Load selection functions without importing the pygame GUI or starting engines."""
import ast
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'main.py').read_text())
ns = dict(os=os, platform=platform, sys=sys, warnings=warnings,
          FOX_CHESS_DIR=str(ROOT / 'engines' / 'fox-chess'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in ('detect_fox_cpu', 'fox_build_order', 'fox_opponents')],
                        type_ignores=[]), 'main.py', 'exec'), ns)


def cpu(vendor='GenuineIntel', family=6, extra=()):
    return dict(vendor_id=vendor, family=family, flags={'avx2', *extra})


class FoxSelectionTests(unittest.TestCase):
    def select(self, info):
        return [(Path(p).name, r) for p, r in ns['fox_opponents'](info)]

    def test_avx2_only_all_versions(self):
        self.assertEqual(self.select(cpu()), [
            ('v1.0-avx2.exe', 2740), ('v1.1-avx2.exe', 2870),
            ('foxchess-current-avx2.exe', 3060)])

    def test_intel_bmi2(self):
        self.assertTrue(all('avx2-bmi2' in p for p, _ in self.select(cpu(extra=['bmi2']))))

    def test_old_amd_avoids_slow_pext(self):
        for family in (0x15, 0x17):
            self.assertEqual(ns['fox_build_order'](cpu('AuthenticAMD', family, ['bmi2'])), ['avx2'])

    def test_zen3_bmi2(self):
        self.assertEqual(ns['fox_build_order'](cpu('AuthenticAMD', 0x19, ['bmi2']))[0], 'avx2-bmi2')

    def test_avx512_only_current_has_build(self):
        selected = self.select(cpu(extra=['bmi2', 'avx512f', 'avx512bw', 'avx512dq', 'avx512vl']))
        self.assertEqual(selected[-1][0], 'foxchess-current-avx512.exe')
        self.assertTrue(all('avx2-bmi2' in p for p, _ in selected[:2]))

    def test_incomplete_avx512(self):
        self.assertNotIn('avx512', ns['fox_build_order'](cpu(extra=['bmi2', 'avx512f'])))

    def test_unknown_and_unsupported_cpu_skip(self):
        with warnings.catch_warnings(record=True):
            self.assertEqual(self.select({}), [])
            self.assertEqual(self.select(dict(flags={'bmi2'})), [])

    def test_missing_preferred_build_falls_back(self):
        with tempfile.TemporaryDirectory() as folder, warnings.catch_warnings(record=True):
            Path(folder, 'v1.0-avx2.exe').touch()
            selected = ns['fox_opponents'](cpu(extra=['bmi2']), folder)
            self.assertEqual([(Path(p).name, r) for p, r in selected], [('v1.0-avx2.exe', 2740)])


if __name__ == '__main__':
    unittest.main()
