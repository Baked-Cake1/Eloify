"""Install Maia networks and the supported Windows Lc0 runtime beside this script.

Run: python engines/maia/install.py
Use --backend cuda12 or --backend onnx-dml to override automatic GPU detection.
Only run this installer if you trust the upstream release: ONNX-DML runs its
bundled install.cmd, which may prompt for permissions or install dependencies.
"""
import argparse
import gzip
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

INSTALL_DIR = Path(__file__).resolve().parent
MAIA_URL = 'https://github.com/CSSLab/maia-chess/releases/download/v1.0/maia-{}.pb.gz'
LC0_URL = 'https://github.com/LeelaChessZero/lc0/releases/download/v0.32.1/lc0-v0.32.1-windows-{}.zip'
PACKAGES = {
    'cuda12': ('gpu-nvidia-cuda12', (
        'mimalloc-override.dll', 'mimalloc-redirect.dll', 'lc0.exe',
        'cudart64_12.dll', 'cublasLt64_12.dll', 'cublas64_12.dll')),
    'onnx-dml': ('onnx-dml', (
        'DirectML.dll', 'lc0.exe', 'mimalloc-override.dll',
        'mimalloc-redirect.dll', 'onnxruntime.dll')),
}


def powershell_json(script):
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
        check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout.strip() or '[]')


def detect_gpus():
    """Query all adapters, including hybrid integrated/discrete configurations."""
    data = powershell_json(
        'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json')
    if isinstance(data, str):
        return [data]
    return data or []


def choose_backend(names):
    # Prefer a supported discrete NVIDIA card over an integrated AMD/Intel GPU.
    for name in names:
        match = re.search(r'\bRTX\s*(\d{4})\b', name, re.I)
        if 'nvidia' in name.lower() and match and int(match[1]) >= 2000:
            return 'cuda12'
    if any(re.search(r'\b(AMD|ATI|Intel)\b', name, re.I) for name in names):
        return 'onnx-dml'
    return None


def cpu_description():
    """Report identity, not the Windows installation date as a CPU release date."""
    try:
        data = powershell_json(
            'Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name | ConvertTo-Json')
        return ', '.join(data) if isinstance(data, list) else str(data)
    except (OSError, ValueError, subprocess.SubprocessError):
        return platform.processor() or 'unknown CPU'


def download(url, destination):
    """Write atomically; interrupted downloads never masquerade as installed files."""
    temporary = destination.with_name(destination.name + '.part')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Eloify-Maia-Installer'})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def valid_network(path):
    try:
        with gzip.open(path, 'rb') as source:
            size = 0
            for block in iter(lambda: source.read(1024 * 1024), b''):
                size += len(block)
        return size > 0
    except (OSError, EOFError):
        return False


def install_networks(folder):
    for elo in range(1100, 2000, 100):
        destination = folder / f'maia-{elo}.pb.gz'
        if destination.is_file() and valid_network(destination):
            print(f'Already installed: {destination.name}')
            continue
        print(f'Downloading Maia {elo}...')
        download(MAIA_URL.format(elo), destination)
        if not valid_network(destination):
            destination.unlink(missing_ok=True)
            raise RuntimeError(f'Invalid gzip network downloaded for Maia {elo}')


def extract_archive(archive, destination):
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            # Reject both POSIX and Windows traversal, drives, and symlinks.
            path = PureWindowsPath(member.filename)
            if (path.drive or path.root or '..' in path.parts or
                    (member.external_attr >> 16) & 0o170000 == 0o120000):
                raise RuntimeError(f'Unsafe archive entry: {member.filename}')
        source.extractall(destination)


def find_unique(folder, name):
    matches = [p for p in folder.rglob('*') if p.is_file() and p.name.lower() == name.lower()]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one {name} in Lc0 package, found {len(matches)}')
    return matches[0]


def install_lc0(backend, folder):
    package, filenames = PACKAGES[backend]
    # Staging is inside the Maia folder; archives and extracted files are removed
    # on success or failure, and never mixed with another backend's archive.
    with tempfile.TemporaryDirectory(prefix='.lc0-install-', dir=folder) as work:
        work = Path(work)
        archive = work / 'lc0.zip'
        print(f'Downloading Lc0 v0.32.1 ({backend})...')
        download(LC0_URL.format(package), archive)
        extracted = work / 'extracted'
        extract_archive(archive, extracted)
        if backend == 'onnx-dml':
            script = find_unique(extracted, 'install.cmd')
            print('Running upstream install.cmd; follow any Windows prompts.')
            subprocess.run(['cmd.exe', '/d', '/c', str(script)], cwd=script.parent, check=True)
        # Validate the complete set before modifying the installed runtime.
        files = [(find_unique(extracted, name), folder / name) for name in filenames]
        for source, target in files:
            shutil.copy2(source, target)
    print(f'Lc0 installed in {folder}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=['auto', *PACKAGES], default='auto',
                        help='Override GPU detection (does not make incompatible hardware supported).')
    args = parser.parse_args(argv)
    if sys_platform_unsupported():
        print('Not supported in this update: Lc0 packages require 64-bit x86 Windows.')
        return 1
    folder = INSTALL_DIR
    folder.mkdir(parents=True, exist_ok=True)
    backend = args.backend
    if backend == 'auto':
        try:
            names = detect_gpus()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            print(f'GPU detection failed: {exc}. Use --backend only if you know your hardware.')
            return 1
        print('Detected GPUs: ' + (', '.join(names) or 'none'))
        backend = choose_backend(names)
    # Networks are useful even when the runtime needs a future installer update.
    install_networks(folder)
    if backend is None:
        print('CPU: ' + cpu_description())
        print('Not supported in this update: older NVIDIA/cuDNN and CPU-only '
              'DNNL/OpenBLAS configurations. No Lc0 runtime was installed.')
        return 1
    install_lc0(backend, folder)
    print('Installed Maia 1100–1900 and Lc0. Existing Eloify engine paths are unchanged.')
    return 0


def sys_platform_unsupported():
    return os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            zipfile.BadZipFile) as exc:
        raise SystemExit(f'Installation failed: {exc}')
