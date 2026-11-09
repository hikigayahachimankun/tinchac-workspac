"""Fixed, named text cases only. Never used as a fallback for live/replay."""
import json
from pathlib import Path
from unicodedata import normalize
from uuid import UUID

from ..models import CheckCreate, CheckResult, SourceChunk, SourcePublic, SourceVersion
from .errors import ServiceError

ROOT = Path(__file__).resolve().parents[3]


class FixtureAdapter:
    def __init__(self):
        self.source = SourceVersion.model_validate_json((ROOT / 'data/fixtures/sources.jsonl').read_text())
        if not self.source.is_fixture or self.source.review_status != 'approved':
            raise ValueError('Expected approved fixture source')
        fact = self.source.facts[0]
        chunk = SourceChunk(chunk_id=self.source.version_id + '_c01', version_id=self.source.version_id,
                            text=fact.quote, source_span=fact.span, section=None, page=None)
        self.public = SourcePublic(schema_version='1.0', **self.source.model_dump(include={
            'version_id', 'title', 'canonical_url', 'published_at', 'retrieved_at', 'is_fixture', 'text'}),
            chunks=[chunk])
        self.chunks = {chunk.chunk_id: chunk}
        self.cases = {}
        for line in (ROOT / 'data/fixtures/cases.jsonl').read_text().splitlines():
            case = json.loads(line)
            self.cases[normalize('NFC', case['confirmed_text']).strip()] = case

    def build_result(self, check_id: UUID, request: CheckCreate) -> CheckResult:
        case = self.cases.get(normalize('NFC', request.confirmed_text).strip())
        if case is None:
            raise ServiceError('NO_CHECKABLE_CLAIM', 'Fixture chỉ hỗ trợ các mẫu định danh. Hãy chọn nội dung mẫu.')
        if case['error']:
            raise ServiceError(case['error'], 'Lỗi worker mô phỏng có chủ đích.', True)
        data = case['result'] | {'check_id': str(check_id), 'as_of': request.as_of.isoformat()}
        # These are scripted outputs, not an extractor or a real verifier.
        result = CheckResult.model_validate(data, context={'chunks': self.chunks})
        if result.run_mode != 'fixture' or any(not s.is_fixture for s in result.sources):
            raise ValueError('Fixture mode required')
        if result.sources and request.as_of < self.source.available_at:
            data['claims'] = [claim.model_dump() | {
                'label': 'insufficient_evidence', 'reason_codes': ['NO_SOURCE'],
                'evidence': [], 'checks_passed': [], 'temporal_status': 'unknown',
                'explanation': 'Snapshot fixture chưa có tại thời điểm đối chiếu.'
            } for claim in result.claims]
            data['sources'] = []
            data['summary'] = dict(supported=0, contradicted=0, insufficient_evidence=len(result.claims),
                                   message='Chưa có nguồn fixture đủ điều kiện tại thời điểm đối chiếu.')
            return CheckResult.model_validate(data)
        return result
