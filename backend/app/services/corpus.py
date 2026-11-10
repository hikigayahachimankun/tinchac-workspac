"""Offline corpus identity, exact source spans, and reproducible chunking."""
from datetime import datetime, time, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from zoneinfo import ZoneInfo

from ..models import SourceChunk, SourceVersion, TextSpan

ROOT = Path(__file__).resolve().parents[3]
RETRIEVAL_CONFIG = {
    'method': 'fts5_tfidf_rrf', 'fts_candidates': 10, 'tfidf_candidates': 10,
    'analyzer': 'char_wb', 'ngram_range': [3, 5], 'rrf_k': 60, 'top_k': 5,
    'tokenizer': 'unicode61 remove_diacritics 2', 'query_version': 'program_year_statement_v1',
}
CHUNK_CONFIG = {'version': 1, 'target_words': 200, 'max_words': 400,
                'oversize_policy': 'keep_atomic_section_table_or_fact', 'pdf_boundary': 'page'}


def normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n'))


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def canonical_hash(value) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))


def implementation() -> dict:
    paths = ['backend/app/services/corpus.py', 'backend/app/services/retrieve.py',
             'scripts/ingest_sources.py', 'scripts/validate_corpus.py', 'backend/app/models.py']
    return {'files': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
            'sqlite': sqlite3.sqlite_version,
            'packages': {p: importlib.metadata.version(p) for p in
                         ('scikit-learn', 'numpy', 'beautifulsoup4', 'PyMuPDF', 'pydantic')}}


def validate_sources(sources: list[SourceVersion], *, is_fixture: bool):
    ids = set()
    by_id = {s.version_id: s for s in sources}
    for source in sources:
        # Re-validate even model_copy callers. Pydantic model instances may otherwise bypass checks.
        SourceVersion.model_validate(source.model_dump(mode='json'))
        if source.version_id in ids or source.is_fixture != is_fixture:
            raise ValueError('Duplicate version or mixed fixture/real corpus')
        ids.add(source.version_id)
        if source.text != normalize_text(source.text) or sha256(source.text) != source.content_sha256:
            raise ValueError('Source NFC/newline/hash mismatch')
        if not source.verified_by.strip() or not source.family_id.strip():
            raise ValueError('Missing reviewer/family')
        if source.review_status == 'approved' and not source.text.strip():
            raise ValueError('Approved source text is empty')
        if not is_fixture:
            expected = 'dut_' + sha256(source.canonical_url)[:16]
            if source.source_id != expected or source.version_id != expected + '_' + source.content_sha256[:16]:
                raise ValueError('Source/version identity mismatch')
            if source.available_basis == 'fixture':
                raise ValueError('Real source has fixture availability')
        if source.available_basis == 'first_seen' and source.available_at != source.retrieved_at:
            raise ValueError('first_seen must equal retrieved_at')
        if source.available_basis == 'published_verified':
            if source.published_precision == 'date':
                earliest = datetime.combine(datetime.fromisoformat(source.published_at).date(), time.max,
                                            ZoneInfo('Asia/Ho_Chi_Minh'))
            elif source.published_precision == 'datetime':
                earliest = datetime.fromisoformat(source.published_at.replace('Z', '+00:00'))
                if earliest.tzinfo is None:
                    raise ValueError('Publication datetime needs an offset')
            else:
                raise ValueError('Verified publication needs a date')
            if source.available_at < earliest:
                raise ValueError('Source made available before verified publication')
        previous = source.supersedes_version_id
        if previous:
            old = by_id.get(previous)
            if old is None or old.family_id != source.family_id or old.scope != source.scope:
                raise ValueError('Supersession needs an existing same-family/scope version')
            if old.available_at >= source.available_at:
                raise ValueError('Supersession must point back in time')


def chunk_source(source: SourceVersion, pages: list[dict] | None = None) -> list[SourceChunk]:
    """Pack whole sections/paragraphs; never bisect a reviewed fact or a PDF page."""
    if pages is None:
        pages = [{'start': 0, 'end': len(source.text), 'page': None}]
    elif [p['page'] for p in pages] != list(range(1, len(pages) + 1)):
        raise ValueError('PDF pages must be numbered from 1 in order')
    cursor = 0
    chunks = []
    for page in pages:
        start, end = page['start'], page['end']
        if start != cursor or end <= start or end > len(source.text):
            raise ValueError('Page spans must partition the normalized text')
        if any(f.span.start < end < f.span.end for f in source.facts):
            raise ValueError('Page boundary bisects a reviewed fact')
        cursor = end
        text = source.text[start:end]
        # Tables remain inside one section. Heading boundaries and blank lines are soft cuts.
        cuts = [start] + [start + m.end() for m in re.finditer(r'\n\n+|\n(?=\d+(?:\.\d+)*\.\s)', text)] + [end]
        cuts = sorted(set(cuts))
        cuts = [p for p in cuts if p in (start, end) or not any(f.span.start < p < f.span.end for f in source.facts)]
        group_start = cuts[0]
        for left, right in zip(cuts, cuts[1:]):
            if left > group_start and len(source.text[group_start:right].split()) > CHUNK_CONFIG['max_words']:
                chunks.append((group_start, left, page['page']))
                group_start = left
        chunks.append((group_start, end, page['page']))
    if cursor != len(source.text):
        raise ValueError('Page map does not cover source')
    result = []
    for start, end, page in chunks:
        if source.text[start:end].strip():
            result.append(SourceChunk(chunk_id=f'{source.version_id}_c{len(result)+1:03}',
                          version_id=source.version_id, text=source.text[start:end],
                          source_span=TextSpan(start=start, end=end), section=None, page=page))
    return result


def build_corpus(sources: list[SourceVersion], *, is_fixture=False, provenance=None,
                 ingest_code_commit='unrecorded') -> tuple[list[SourceChunk], dict]:
    validate_sources(sources, is_fixture=is_fixture)
    provenance = provenance or {}
    chunks = []
    for source in sorted(sources, key=lambda s: s.version_id):
        if source.review_status == 'approved':
            chunks.extend(chunk_source(source, provenance.get(source.version_id, {}).get('pages')))
    identity = {
        'format': 1, 'is_fixture': is_fixture, 'chunking': CHUNK_CONFIG,
        'retrieval': RETRIEVAL_CONFIG, 'implementation': implementation(),
        'source_versions': [{'version_id': s.version_id, 'content_sha256': s.content_sha256,
                             'metadata_sha256': canonical_hash(s.model_dump(mode='json'))}
                            for s in sorted(sources, key=lambda s: s.version_id)],
        'chunks_sha256': canonical_hash([c.model_dump(mode='json') for c in chunks]),
        'provenance': provenance,
        'source_count': len(sources), 'indexed_source_count': sum(s.review_status == 'approved' for s in sources),
        'excluded_versions': sorted(s.version_id for s in sources if s.review_status != 'approved'),
        'ingest_code_commit': ingest_code_commit,
        # A logical build timestamp makes the whole manifest reproducible, including offline rebuilds.
        'build_at': max((s.retrieved_at for s in sources), default=datetime(1970,1,1,tzinfo=timezone.utc)).isoformat(),
    }
    manifest = identity | {'corpus_version': 'corpus-' + canonical_hash(identity)}
    return chunks, manifest


def validate_corpus(sources: list[SourceVersion], chunks: list[SourceChunk], manifest: dict):
    expected_version = 'corpus-' + canonical_hash({k:v for k,v in manifest.items() if k != 'corpus_version'})
    if expected_version != manifest['corpus_version']:
        raise ValueError('Manifest identity mismatch')
    expected_chunks, expected_manifest = build_corpus(sources, is_fixture=manifest['is_fixture'],
        provenance=manifest['provenance'], ingest_code_commit=manifest['ingest_code_commit'])
    if manifest != expected_manifest or chunks != expected_chunks:
        raise ValueError('Corpus, code/config or chunk hash/span mismatch; rebuild the snapshot')
    by_id = {s.version_id: s for s in sources}
    for chunk in chunks:
        SourceChunk.model_validate(chunk.model_dump(mode='json'))
        source = by_id[chunk.version_id]
        if source.review_status != 'approved' or chunk.text != source.text[chunk.source_span.start:chunk.source_span.end]:
            raise ValueError('Chunk does not match approved normalized source')


def load_corpus(directory: Path):
    sources = [SourceVersion.model_validate(s) for s in json.loads((directory / 'sources.json').read_text())]
    chunks = [SourceChunk.model_validate(c) for c in json.loads((directory / 'chunks.json').read_text())]
    manifest = json.loads((directory / 'manifest.json').read_text())
    validate_corpus(sources, chunks, manifest)
    return sources, chunks, manifest
