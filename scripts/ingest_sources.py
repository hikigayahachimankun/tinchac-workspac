"""Rebuild approved corpus from local snapshots only; never downloads URLs."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
import pymupdf

from backend.app.models import SourceVersion
from backend.app.services.corpus import ROOT, build_corpus, normalize_text, validate_corpus


def extract_html(path: Path, selector: str) -> str:
    soup = BeautifulSoup(path.read_bytes(), 'html.parser')
    content = soup.select_one(selector)
    if content is None:
        raise ValueError('Approved HTML selector is missing')
    for tag in content.select('h2, .wd-date, .wd-notify-hot, script, style, iframe'):
        tag.decompose()
    for table in content.select('table'):
        # One atomic line prevents numbered rows or blank cells becoming chunk boundaries.
        table.replace_with(table.get_text(' | ', strip=True))
    return normalize_text(content.get_text('\n', strip=True))


def extract_pdf(path: Path) -> tuple[str, list[dict]]:
    parts, pages, start = [], [], 0
    with pymupdf.open(path) as document:
        for number, page in enumerate(document, 1):
            text = normalize_text(page.get_text(sort=True)).strip() + '\n'
            if not text.strip():
                raise ValueError('PDF has a blank/scanned page; supply a reviewed manual extract')
            parts.append(text)
            pages.append({'start': start, 'end': start + len(text), 'page': number})
            start += len(text)
    if not parts:
        raise ValueError('PDF has no pages')
    return ''.join(parts), pages


def checked_file(root: Path, entry: dict) -> Path:
    path = (root / entry['path']).resolve()
    if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
        raise ValueError('Raw snapshot path/hash mismatch')
    return path


def validate_register(sources, register):
    """The exact T02 URL allowlist is also the review/provenance boundary."""
    entries = {row['version_id']: row for row in register['sources']}
    if len(entries) != len(register['sources']) or set(entries) != {s.version_id for s in sources}:
        raise ValueError('Register and snapshot versions differ')
    provenance = {}
    by_id = {s.version_id:s for s in sources}
    for source in sources:
        entry = entries[source.version_id]
        notice = urlsplit(entry['notice_url'])
        if notice.scheme != 'https' or notice.hostname != entry['notice_host'] or notice.path != entry['notice_path']:
            raise ValueError('Notice outside approved host/path')
        for field in ('source_id', 'family_id', 'canonical_url', 'review_status'):
            if entry[field] != getattr(source, field):
                raise ValueError('Register metadata differs from snapshot')
        if source.canonical_url != entry['notice_url']:
            if source.parent_url != entry['notice_url'] or source.canonical_url not in entry.get('approved_content_urls', []):
                raise ValueError('Attachment not explicitly approved under its parent notice')
        receipt = entry['ingest']
        if receipt['normalized_sha256'] != source.content_sha256 or not receipt['reviewed_by'].strip():
            raise ValueError('Missing text hash/reviewer provenance')
        for file in [receipt.get('raw')] + ([receipt.get('manual_text')] if receipt['method'] == 'manual_pdf' else []):
            if not file or not file.get('path') or not re.fullmatch('[0-9a-f]{64}', file.get('sha256', '')):
                raise ValueError('Missing local snapshot path/SHA-256 provenance')
        if datetime.fromisoformat(receipt['snapshot_retrieved_at'].replace('Z', '+00:00')) != source.retrieved_at:
            raise ValueError('Snapshot retrieval time differs from provenance')
        if receipt['method'] not in ('html', 'pdf_text', 'manual_pdf', 'quarantine_metadata'):
            raise ValueError('Unsupported ingest method')
        if source.review_status == 'approved' and receipt['method'] == 'quarantine_metadata':
            raise ValueError('Quarantine metadata cannot be promoted to approved evidence')
        if receipt['method'] in ('pdf_text', 'manual_pdf'):
            if not receipt.get('pages') or source.parent_url is None:
                raise ValueError('PDF requires page spans and parent URL')
        if receipt['method'] == 'manual_pdf' and (not receipt.get('manual_text') or not receipt.get('notes')):
            raise ValueError('Manual extract requires file/hash and a description of omissions')
        if source.supersedes_version_id:
            relation = receipt.get('supersession') or {}
            old = by_id.get(source.supersedes_version_id)
            if (old is None or relation.get('version_id') != old.version_id or not relation.get('reviewed_by')
                    or not relation.get('quote') or relation['quote'] not in source.text):
                raise ValueError('Supersession needs reviewed exact evidence in the new source')
        provenance[source.version_id] = receipt
    return provenance


def ingest(snapshot: Path, register_path: Path, output: Path, *, from_raw=False, root=ROOT):
    sources = [SourceVersion.model_validate(s) for s in json.loads(snapshot.read_text())]
    register = json.loads(register_path.read_text())  # JSON is a YAML 1.2 subset, per D08.
    provenance = validate_register(sources, register)
    if from_raw:
        entries = {e['version_id']:e for e in register['sources']}
        for source in sources:
            if source.review_status != 'approved':
                continue  # Do not reopen the quarantined personal-data attachment.
            entry = entries[source.version_id]
            receipt = provenance[source.version_id]
            raw = checked_file(root, receipt['raw'])
            if receipt['method'] == 'html':
                text = extract_html(raw, entry['content_selector'])
            elif receipt['method'] == 'pdf_text':
                text, pages = extract_pdf(raw)
                if pages != receipt['pages']:
                    raise ValueError('PDF page map changed')
            elif receipt['method'] == 'manual_pdf':
                text = normalize_text(checked_file(root, receipt['manual_text']).read_text()).rstrip('\n')
                # Local reviewer read every page; extraction is intentionally not raw OCR.
                with pymupdf.open(raw) as doc:
                    if len(doc) != len(receipt['pages']):
                        raise ValueError('Manual PDF page count differs')
            else:
                raise ValueError('Approved source has no ingest parser')
            if text != source.text:
                raise ValueError(f'Extraction differs from reviewed snapshot: {source.version_id}; review a new version')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    chunks, manifest = build_corpus(sources, provenance=provenance, ingest_code_commit=commit)
    validate_corpus(sources, chunks, manifest)
    existing = output / 'sources.json'
    if existing.exists():
        incoming = {s.version_id: s for s in sources}
        for row in json.loads(existing.read_text()):
            old = SourceVersion.model_validate(row)
            if old.version_id not in incoming or old != incoming[old.version_id]:
                raise ValueError('Cannot drop or rewrite an existing version; use a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    # Manifest written last; a partial build fails validation instead of serving mixed versions.
    for name, value in [('sources', [s.model_dump(mode='json') for s in sources]),
                        ('chunks', [c.model_dump(mode='json') for c in chunks]), ('manifest', manifest)]:
        target = output / f'{name}.json'
        if name == 'sources' and target.resolve() == snapshot.resolve():
            continue
        target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'data/corpus/sources.json')
    parser.add_argument('--register', type=Path, default=ROOT / 'config/sources.yaml')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/corpus')
    parser.add_argument('--from-raw', action='store_true', help='Also verify raw local HTML/PDF/manual extraction')
    args = parser.parse_args()
    manifest = ingest(args.snapshot, args.register, args.output, from_raw=args.from_raw)
    print(f"{manifest['corpus_version']}: {manifest['indexed_source_count']} indexed, {len(manifest['excluded_versions'])} excluded")


if __name__ == '__main__':
    main()
