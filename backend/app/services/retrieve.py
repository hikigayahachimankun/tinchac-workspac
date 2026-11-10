"""Local, eligible-only BM25/character TF-IDF retrieval. No network or verdicts."""
from collections import OrderedDict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from threading import Lock
import time

from sklearn.feature_extraction.text import TfidfVectorizer

from ..models import Claim, RetrievalBundle, RetrievalHit
from .corpus import ROOT, canonical_hash, load_corpus, normalize_text, validate_corpus
from .errors import ServiceError


def query_for(claim: Claim) -> str:
    return normalize_text(' '.join(v for v in (claim.scope.program, claim.scope.academic_year, claim.statement) if v))


def _connection():
    return sqlite3.connect(':memory:')


class Retriever:
    """One immutable snapshot per instance. Queries may run on separate worker threads."""
    def __init__(self, sources, chunks, manifest, *, method='fts5_tfidf_rrf'):
        validate_corpus(sources, chunks, manifest)
        if method not in ('fts5_tfidf_rrf', 'fts5_only'):
            raise ValueError('Unknown retrieval method')
        # Own deep copies: callers must not mutate a loaded snapshot behind its version.
        self._sources = {s.version_id: s.model_copy(deep=True) for s in sources if s.review_status == 'approved'}
        self._chunks = [c.model_copy(deep=True) for c in chunks]
        self.corpus_version = manifest['corpus_version']
        self._config = dict(manifest['retrieval'], method=method)
        self._config_hash = canonical_hash(self._config)
        self._cache = OrderedDict()
        self._lock = Lock()

    @classmethod
    def from_directory(cls, directory: Path = ROOT / 'data/corpus', **kwargs):
        try:
            return cls(*load_corpus(directory), **kwargs)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ServiceError('CORPUS_UNAVAILABLE', 'Snapshot kho nguồn không hợp lệ hoặc chưa được dựng.') from exc

    def _rank(self, chunks, query):
        """Build statistics on eligible chunks, before either candidate limit is applied."""
        # shortcut: rebuild a small in-memory index per uncached query for the solo demo corpus.
        # No persistent query text or shared SQLite connection; revisit after measured corpus growth.
        try:
            with closing(_connection()) as db:
                db.execute('CREATE VIRTUAL TABLE chunk_fts USING fts5(chunk_id UNINDEXED, text, '
                           "tokenize='unicode61 remove_diacritics 2')")
                db.executemany('INSERT INTO chunk_fts VALUES (?,?)', [(c.chunk_id, c.text) for c in chunks])
                # Quote every token. User text cannot inject FTS operators or SQL.
                tokens = sorted(set(re.findall(r'[^\W_]+', query, re.UNICODE)))
                expression = ' OR '.join('"' + token + '"' for token in tokens)
                fts = [] if not expression else [row[0] for row in db.execute(
                    'SELECT chunk_id FROM chunk_fts WHERE chunk_fts MATCH ? '
                    'ORDER BY bm25(chunk_fts), chunk_id LIMIT ?', (expression, self._config['fts_candidates']))]
        except sqlite3.Error as exc:
            raise ServiceError('CORPUS_UNAVAILABLE', 'FTS5 không khả dụng; không thể truy xuất kho nguồn.') from exc
        rankings = [fts]
        if self._config['method'] == 'fts5_tfidf_rrf':
            vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
            try:
                matrix = vectorizer.fit_transform([c.text for c in chunks])
            except ValueError as exc:
                if 'empty vocabulary' not in str(exc):
                    raise
                rankings.append([])
            else:
                scores = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
                order = sorted(range(len(chunks)), key=lambda i: (-float(scores[i]), chunks[i].chunk_id))
                rankings.append([chunks[i].chunk_id for i in order if scores[i] > 0][:self._config['tfidf_candidates']])
        fused = {}
        for ranking in rankings:
            for rank, chunk_id in enumerate(ranking, 1):
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (self._config['rrf_k'] + rank)
        return sorted(fused.items(), key=lambda pair: (-pair[1], pair[0]))

    def retrieve_claim(self, claim: Claim, corpus_version: str, as_of: datetime, k: int = 5,
                       *, public: bool = False) -> RetrievalBundle:
        if corpus_version != self.corpus_version:
            raise ServiceError('CORPUS_UNAVAILABLE', 'Không tìm thấy đúng phiên bản kho nguồn yêu cầu.')
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError('as_of needs a timezone offset')
        if type(k) is not int or not 1 <= k <= 6:
            raise ValueError('k must be between 1 and 6')
        as_of = as_of.astimezone(timezone.utc)
        query = query_for(claim)
        key = canonical_hash({'model':'local-retrieval', 'prompt_hash':canonical_hash('program_year_statement_v1'),
            'schema_version':'1.0', 'input_hash':canonical_hash(claim.model_dump(mode='json')),
            'corpus_version':corpus_version, 'as_of':as_of.isoformat(), 'config_hash':self._config_hash, 'k':k})
        if public:
            with self._lock:
                now = time.monotonic()
                for old_key, (expires, _) in list(self._cache.items()):
                    if expires <= now:
                        del self._cache[old_key]
                if key in self._cache:
                    self._cache.move_to_end(key)
                    return self._cache[key][1].model_copy(deep=True)
        eligible = {version for version, s in self._sources.items() if s.available_at <= as_of}
        chunks = [c for c in self._chunks if c.version_id in eligible]
        ranked = self._rank(chunks, query) if chunks else []
        by_id = {c.chunk_id:c for c in chunks}
        hits = [RetrievalHit(chunk_id=chunk_id, version_id=by_id[chunk_id].version_id,
                  rank=rank, score=score, retriever='rrf', text=by_id[chunk_id].text,
                  source=self._sources[by_id[chunk_id].version_id].model_copy(deep=True))
                for rank, (chunk_id, score) in enumerate(ranked[:k], 1)]
        result = RetrievalBundle(claim_id=claim.claim_id, query=query, hits=hits,
            corpus_version=corpus_version, as_of=as_of,
            reason='found' if hits else ('no_match' if chunks else 'no_eligible_source'))
        if public:
            with self._lock:
                self._cache[key] = (time.monotonic() + 24*3600, result.model_copy(deep=True))
                while len(self._cache) > 64:
                    self._cache.popitem(last=False)
        return result


def retrieve_claim(claim: Claim, corpus_version: str, as_of: datetime, k: int = 5) -> RetrievalBundle:
    """T01 interface. T08 can own a Retriever instance to reuse public query cache.

    CPU work: call through a worker thread from async jobs. Keep one returned bundle
    for B/C/C_NO_TIME; do not retrieve again per system. T11 owns replay persistence.
    """
    return Retriever.from_directory().retrieve_claim(claim, corpus_version, as_of, k)
