"""Public conclusion templates. No LLM rewrite or sender/account certification."""
from datetime import datetime
from uuid import UUID

from ..models import CheckResult, ClaimVerdict, RetrievalBundle, RunMode, SourceSummary, Summary, Usage
from .evidence import join_inputs
from .errors import ServiceError


def combine_usage(*items: Usage) -> Usage:
    if len({(u.provider, u.model) for u in items}) != 1:
        raise ValueError('Cannot combine different provider/model usages')
    return Usage(provider=items[0].provider, model=items[0].model,
                 **{key: sum(getattr(u, key) for u in items) for key in
                    ('input_tokens', 'output_tokens', 'cost_usd', 'cost_vnd_estimate', 'attempts', 'duration_ms')},
                 cache_hit=all(u.cache_hit for u in items))


def build_result(check_id: UUID, verdicts: list[ClaimVerdict], bundles: list[RetrievalBundle],
                 as_of: datetime, run_mode: RunMode, usage: Usage, *, warnings=(),
                 corpus_updated_at: datetime | None = None) -> CheckResult:
    join_inputs(verdicts, bundles)
    if any(b.as_of != as_of for b in bundles):
        raise ServiceError('CORPUS_UNAVAILABLE', 'Thời điểm kết quả không khớp bundle.')
    all_sources = {h.version_id: h.source for b in bundles for h in b.hits}
    cited = {e.version_id for c in verdicts for e in c.evidence}
    if any((run_mode == 'fixture') != source.is_fixture for source in all_sources.values()):
        raise ServiceError('CORPUS_UNAVAILABLE', 'Không trộn nguồn fixture và corpus thật.')
    sources = [SourceSummary(**all_sources[v].model_dump(include=set(SourceSummary.model_fields))) for v in sorted(cited)]
    counts = {label: sum(c.label == label for c in verdicts) for label in ('supported', 'contradicted', 'insufficient_evidence')}
    message = ('Có chi tiết mâu thuẫn và chi tiết chưa xác minh.' if counts['contradicted'] and counts['insufficient_evidence'] else
               'Có chi tiết mâu thuẫn với nguồn.' if counts['contradicted'] else
               'Có chi tiết chưa đủ bằng chứng.' if counts['insufficient_evidence'] else
               'Các trường đã đối chiếu được nguồn hỗ trợ trong phạm vi đã kiểm tra.')
    steps = ['Mở nguồn và kiểm tra đúng chương trình, năm, đối tượng trước khi làm theo thông báo.',
             'TinChắc không xác minh người gửi hoặc chủ tài khoản; xác nhận yêu cầu chuyển tiền qua kênh chính thức.']
    if counts['insufficient_evidence']:
        steps.append('Hỏi đơn vị công bố về nội dung chưa xác minh; bổ sung năm, loại phí hoặc nguồn còn thiếu.')
    if any(c.temporal_status == 'expired' for c in verdicts):
        steps.append('Mốc thời gian đã qua; hỏi đơn vị công bố xem có gia hạn phù hợp hay không.')
    if corpus_updated_at is None:
        if not all_sources:
            raise ServiceError('CORPUS_UNAVAILABLE', 'Cần thời điểm cập nhật snapshot khi bundle rỗng.')
        corpus_updated_at = max(s.retrieved_at for s in all_sources.values())
    return CheckResult(schema_version='1.0', check_id=check_id, claims=verdicts,
        summary=Summary(**counts, message=message), sources=sources, as_of=as_of,
        corpus_version=bundles[0].corpus_version, corpus_updated_at=corpus_updated_at,
        warnings=list(warnings), run_mode=run_mode, next_steps=steps, usage=usage)
