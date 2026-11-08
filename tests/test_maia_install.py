import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location(
    'maia_install', Path(__file__).resolve().parents[1] / 'engines/maia/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_rtx_and_hybrid(self):
        for generation in ('2060', '3080', '4090', '5090'):
            self.assertEqual(installer.choose_backend([
                'Intel UHD Graphics', f'NVIDIA GeForce RTX {generation}']), 'cuda12')

    def test_directml(self):
        for name in ('AMD Radeon RX 7800 XT', 'Intel Arc A770'):
            self.assertEqual(installer.choose_backend([name]), 'onnx-dml')

    def test_unsupported(self):
        for names in ([], ['NVIDIA GeForce GTX 640'], ['NVIDIA GeForce GTX 1660']):
            self.assertIsNone(installer.choose_backend(names))

    def test_traversal_rejected(self):
        for name in ('../evil', 'C:/evil', r'..\evil'):
            with tempfile.TemporaryDirectory() as folder:
                archive = Path(folder) / 'test.zip'
                with zipfile.ZipFile(archive, 'w') as output:
                    output.writestr(name, 'bad')
                with self.assertRaises(RuntimeError):
                    installer.extract_archive(archive, Path(folder) / 'out')

    def test_runtime_install_and_cleanup(self):
        for backend in installer.PACKAGES:
            with self.subTest(backend=backend), tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                def fake_download(url, destination):
                    with zipfile.ZipFile(destination, 'w') as archive:
                        for name in installer.PACKAGES[backend][1]:
                            archive.writestr('package/' + name, b'runtime')
                        if backend == 'onnx-dml':
                            archive.writestr('package/install.cmd', '@exit /b 0')
                with patch.object(installer, 'download', side_effect=fake_download), \
                     patch.object(installer.subprocess, 'run') as run:
                    installer.install_lc0(backend, folder)
                    self.assertEqual(run.call_count, int(backend == 'onnx-dml'))
                self.assertEqual(sorted(p.name for p in folder.iterdir()),
                                 sorted(installer.PACKAGES[backend][1]))

    def test_all_nine_networks(self):
        import gzip
        urls = []
        def fake_download(url, destination):
            urls.append(url)
            destination.write_bytes(gzip.compress(b'network'))
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(installer, 'download', side_effect=fake_download):
            installer.install_networks(Path(folder))
            installer.install_networks(Path(folder))
        self.assertEqual(urls, [installer.MAIA_URL.format(elo) for elo in range(1100, 2000, 100)])


if __name__ == '__main__':
    unittest.main()
