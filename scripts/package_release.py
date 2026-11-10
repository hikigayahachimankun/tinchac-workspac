"""Build an internal fixture RC; never archive the workspace wholesale."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    'README.md', 'requirements.in', 'requirements.lock.txt', '.python-version', '.nvmrc',
    'frontend/package.json', 'frontend/package-lock.json', 'frontend/vite.config.ts',
    'config/experiments.yaml', 'scripts/package_release.py', 'scripts/cold_start_release.py',
    'scripts/__init__.py', 'scripts/init_db.py', 'scripts/release_smoke.py',
    'docs/demo_script.md', 'docs/ai_usage.md', 'reports/release_checklist.md',
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package(root: Path, output: Path) -> dict:
    if not (root / 'frontend/dist/index.html').is_file():
        raise ValueError('Build the HTTP frontend before packaging')
    # Deliberate allowlist: no .env, raw/private/gold, real source snapshots,
    # node_modules, venv, vendor binaries, historical evidence or Git metadata.
    patterns = ['backend/app/**/*.py', 'frontend/src/**/*', 'frontend/dist/**/*',
                'frontend/tests/**/*', 'frontend/tsconfig*.json', 'frontend/playwright*.ts',
                'frontend/index.html', 'contracts/**/*.json', 'data/fixtures/**/*']
    paths = {root / n for n in REQUIRED_FILES}
    for pattern in patterns:
        paths.update(p for p in root.glob(pattern) if p.is_file())
    payload = {}
    for path in sorted(paths):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Symlink/outside path refused: {relative}')
        if ({'__pycache__', 'node_modules'} & set(relative.parts)
                or path.suffix == '.tsbuildinfo'
                or (relative.as_posix() not in REQUIRED_FILES
                    and any(p.startswith('.') for p in relative.parts))):
            continue
        payload[relative.as_posix()] = path.read_bytes()
    corpus = root / 'data/corpus/manifest.json'
    manifest = {
        'schema_version': '1.0', 'kind': 'internal-fixture-release-candidate',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'working_tree_changes': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root)),
        'run_mode': 'fixture', 'active_model': 'fixture-v1', 'active_corpus': 'fixture-v1',
        'configured_live_model': json.loads((root / 'config/experiments.yaml').read_text())['model'],
        'live_enabled': False, 'workers': 1,
        'experiment_seed': json.loads((root / 'config/experiments.yaml').read_text())['seed'],
        'reference_corpus_manifest_sha256': sha(corpus.read_bytes()) if corpus.exists() else None,
        'reference_corpus_included': False,
        'files': {name: sha(data) for name, data in payload.items()},
        'limits': ['Second physical machine unverified', 'Not live or benchmark acceptance',
                   'Internal use; external redistribution rights not cleared'],
    }
    payload['release-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    # Exclusive create prevents silently replacing another candidate.
    with output.open('xb') as stream, tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, data in payload.items():
            info = tarfile.TarInfo('tinchac/' + name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            archive.addfile(info, io.BytesIO(data))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New .tar.gz path, outside Git')
    args = parser.parse_args()
    manifest = package(ROOT, args.output)
    print(json.dumps({'files': len(manifest['files']), 'sha256': sha(args.output.read_bytes()),
                      'output': str(args.output), 'kind': manifest['kind']}, indent=2))


if __name__ == '__main__':
    main()
