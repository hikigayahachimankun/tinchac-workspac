import io
import json
from pathlib import Path
import tarfile

import pytest

from scripts import package_release
from scripts.cold_start_release import cold_start


def build_tree(path):
    project = Path(__file__).resolve().parents[2]
    for name in package_release.REQUIRED_FILES:
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((project / name).read_bytes())
    for name in ('frontend/dist/index.html', 'data/fixtures/cases.jsonl',
                 'data/private/secret.json', 'data/raw/raw.png', 'data/corpus/sources.json',
                 '.env', 'frontend/.env.local', 'frontend/src/.env.local',
                 'data/fixtures/.env', 'frontend/src/node_modules/private.json', 'frontend/notes.json'):
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('synthetic test marker')
    return path


def test_package_excludes_private_data_and_refuses_overwrite(tmp_path, monkeypatch):
    root = build_tree(tmp_path / 'project')
    monkeypatch.setattr(package_release.subprocess, 'check_output', lambda *a, **kw: 'base' if kw.get('text') else b'')
    archive = tmp_path / 'rc.tar.gz'
    manifest = package_release.package(root, archive)
    with tarfile.open(archive) as bundle:
        names = bundle.getnames()
        assert 'tinchac/frontend/dist/index.html' in names
        assert 'tinchac/data/fixtures/cases.jsonl' in names
        assert 'tinchac/frontend/notes.json' not in names
        for name in names:
            parts = Path(name).parts
            assert not {'private', 'raw', 'corpus', '.venv', 'node_modules', '__pycache__'} & set(parts)
            assert not any(p.startswith('.env') for p in parts)
        assert json.load(bundle.extractfile('tinchac/release-manifest.json'))['files'] == manifest['files']
    with pytest.raises(FileExistsError):
        package_release.package(root, archive)


def test_package_requires_build_and_refuses_symlink(tmp_path):
    with pytest.raises(ValueError, match='Build'):
        package_release.package(tmp_path, tmp_path / 'missing.tar.gz')
    build_tree(tmp_path)
    (tmp_path / 'frontend/dist/index.html').unlink()
    (tmp_path / 'frontend/dist/index.html').symlink_to('/etc/passwd')
    with pytest.raises(ValueError, match='Symlink'):
        package_release.package(tmp_path, tmp_path / 'leak.tar.gz')


def test_cold_start_refuses_archive_traversal_and_existing_output(tmp_path):
    archive = tmp_path / 'malicious.tar.gz'
    with tarfile.open(archive, 'w:gz') as bundle:
        info = tarfile.TarInfo('tinchac/../../escape')
        info.size = 1
        bundle.addfile(info, io.BytesIO(b'x'))
    with pytest.raises(ValueError, match='Unexpected archive'):
        cold_start(archive, tmp_path / 'new')
    assert not (tmp_path / 'escape').exists()
    with pytest.raises(FileExistsError):
        cold_start(archive, tmp_path / 'new')
