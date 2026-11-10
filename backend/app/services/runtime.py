"""One validated, immutable local corpus shared by HTTP jobs and source snapshots."""
from pathlib import Path

from ..models import SourcePublic, SourceSummary
from .corpus import load_corpus
from .errors import ServiceError
from .retrieve import Retriever


class LiveRuntime:
    def __init__(self, directory: Path):
        try:
            sources, chunks, manifest = load_corpus(directory)
            if manifest['is_fixture'] or not any(s.review_status == 'approved' for s in sources):
                raise ValueError('Live requires approved real sources')
            self.retriever = Retriever(sources, chunks, manifest)
            self.updated_at = max(s.retrieved_at for s in sources if s.review_status == 'approved')
            self.sources = {s.version_id: SourcePublic(schema_version='1.0',
                **s.model_dump(include=set(SourceSummary.model_fields)), text=s.text,
                chunks=[c for c in chunks if c.version_id == s.version_id])
                for s in sources if s.review_status == 'approved'}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ServiceError('CORPUS_UNAVAILABLE', 'Snapshot kho nguồn không hợp lệ hoặc chưa được dựng.', status=503) from exc

    def source(self, version_id: str) -> SourcePublic:
        if version_id not in self.sources:
            raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy snapshot.', status=404)
        return self.sources[version_id].model_copy(deep=True)
