"""Extract an RC into a NEW directory, install locks and run README fixture smoke.

Uses a separate venv and npm install. This does not certify a second machine.
Requires uv, Python 3.11.18, Node 22.23.4 and local Tesseract vie+eng.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import tarfile
import time
from urllib.request import build_opener, ProxyHandler


def cold_start(archive: Path, output: Path):
    output.mkdir(mode=0o700)  # Never overwrite/reuse an earlier run.
    with tarfile.open(archive, 'r:gz') as bundle:
        for entry in bundle.getmembers():
            path = Path(entry.name)
            if not entry.isfile() or path.is_absolute() or '..' in path.parts or path.parts[0] != 'tinchac':
                raise ValueError('Unexpected archive entry')
        bundle.extractall(output, filter='data')
    root = output / 'tinchac'
    manifest = json.loads((root / 'release-manifest.json').read_text())
    for name, expected in manifest['files'].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Invalid manifest path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Package hash mismatch: ' + name)
    # Fresh environment; no workspace .env, VITE flags, provider keys or proxy.
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'SYSTEMROOT') if k in os.environ}
    env.update(APP_MODE='fixture', LLM_LIVE_ENABLED='false', GEMINI_API_KEY='', VITE_API_MODE='http',
               FRONTEND_DIST='./frontend/dist', DATABASE_PATH='./data/private/demo.sqlite3',
               PRIVATE_DIR='./data/private', UV_PYTHON_DOWNLOADS='never')
    commands = []

    def run(command):
        commands.append(command)
        result = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True)
        with (output / 'install.log').open('a') as log:
            log.write(result.stdout + result.stderr)
        result.check_returncode()
        return result.stdout

    try:
        node = run(['node', '--version']).strip()
        if node != 'v' + (root / '.nvmrc').read_text().strip():
            raise ValueError('Use the pinned Node version')
        run(['uv', 'venv', '--python', (root / '.python-version').read_text().strip(), '.venv'])
        run(['uv', 'pip', 'sync', '--python', '.venv/bin/python', 'requirements.lock.txt'])
        run(['uv', 'pip', 'check', '--python', '.venv/bin/python'])
        run(['npm', 'ci', '--prefix', 'frontend', '--cache', str(output / 'npm-cache')])
        run(['npm', 'run', 'build', '--prefix', 'frontend'])
        run(['.venv/bin/python', '-m', 'scripts.init_db'])
        languages = run(['tesseract', '--list-langs'])
        assert {'vie', 'eng'} <= set(languages.split())
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        command = ['.venv/bin/python', '-m', 'uvicorn', 'backend.app.main:app', '--host',
                   '127.0.0.1', '--port', str(port), '--workers', '1']
        commands.append(command)
        with (output / 'server.log').open('w') as log:
            server = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log)
            try:
                opener = build_opener(ProxyHandler({}))
                base = f'http://127.0.0.1:{port}'
                for _ in range(100):
                    try:
                        with opener.open(base + '/api/v1/health', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError('Server exited; see server.log')
                        time.sleep(.1)
                result = json.loads(run(['.venv/bin/python', '-m', 'scripts.release_smoke', '--base-url', base]))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
        result.update(environment='fresh extracted tree and venv on SAME host',
                      second_machine_verified=False, os=platform.platform(), node=node,
                      python=run(['.venv/bin/python', '--version']).strip(),
                      archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                      package_commit=manifest['git_commit'])
        (output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New absolute directory')
    args = parser.parse_args()
    cold_start(args.archive.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
