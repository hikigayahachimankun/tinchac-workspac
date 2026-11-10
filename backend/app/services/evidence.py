"""C guard: exact citations and reviewed, scoped facts. No provider I/O."""
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
import logging
import re
from zoneinfo import ZoneInfo

from ..models import (Claim, ClaimVerdict, EvidenceRef, RetrievalBundle, RetrievalHit, SourceFact, SourceVersion,
                      TemporalCheckReport, TextSpan, VerdictDraft, check_quote)
from .corpus import sha256
from .errors import ServiceError
from .normalization import folded, normalize_url, scope_compatible

logger = logging.getLogger(__name__)
VN = ZoneInfo('Asia/Ho_Chi_Minh')


def join_inputs(claims, bundles, temporal=None):
    ids = [c.claim_id for c in claims]
    if not ids or len(set(ids)) != len(ids):
        raise ServiceError('PROVIDER_BAD_OUTPUT', 'Danh sách claim thiếu hoặc trùng ID.')
    for rows in (bundles, *([temporal] if temporal is not None else [])):
        if len(rows) != len(ids) or {r.claim_id for r in rows} != set(ids):
            raise ServiceError('PROVIDER_BAD_OUTPUT', 'Không ghép được claim, bundle hoặc temporal report.')
    if len({(b.corpus_version, b.as_of) for b in bundles}) != 1:
        raise ServiceError('CORPUS_UNAVAILABLE', 'Bundle không cùng snapshot và thời điểm.')
    chunks, versions = {}, {}
    for bundle in bundles:
        for hit in bundle.hits:
            source = hit.source
            try:
                SourceVersion.model_validate(source.model_dump())
            except ValueError:
                raise ServiceError('CORPUS_UNAVAILABLE', 'Fact hoặc metadata nguồn không hợp lệ.') from None
            if (hit.version_id != source.version_id or not hit.text or hit.text not in source.text
                    or sha256(source.text) != source.content_sha256):
                raise ServiceError('CORPUS_UNAVAILABLE', 'Hit không khớp snapshot nguồn.')
            for key, data, index in ((hit.chunk_id, (hit.version_id, hit.text), chunks),
                                     (source.version_id, source.model_dump(), versions)):
                if key in index and index[key] != data:
                    raise ServiceError('CORPUS_UNAVAILABLE', 'ID nguồn hoặc chunk không nhất quán.')
                index[key] = data
    return {b.claim_id: b for b in bundles}


def eligible_hits(bundle: RetrievalBundle):
    hits = [h for h in bundle.hits if h.source.review_status == 'approved'
            and h.source.available_at <= bundle.as_of]
    # A reviewed replacement only takes over once effective. Merely newer is not enough.
    replaced = set()
    for new in hits:
        for old in hits:
            start = new.source.effective_from
            active = start is None or (not start.ambiguous and start.value is not None and
                (datetime.fromisoformat(start.value).astimezone(VN) <= bundle.as_of.astimezone(VN)
                 if start.precision == 'datetime' else
                 datetime.fromisoformat(start.value).date() <= bundle.as_of.astimezone(VN).date()))
            if (new.source.supersedes_version_id == old.version_id and active
                    and new.source.family_id == old.source.family_id
                    and new.source.scope == old.source.scope
                    and old.source.available_at < new.source.available_at):
                replaced.add(old.version_id)
    return [h for h in hits if h.version_id not in replaced]


@dataclass
class FactMatch:
    hit: RetrievalHit
    fact: SourceFact
    start: int

    def citation(self, relation='context'):
        return EvidenceRef(chunk_id=self.hit.chunk_id, version_id=self.hit.version_id,
                           quote=self.fact.quote, quote_span=TextSpan(start=self.start, end=self.start + len(self.fact.quote)),
                           relation=relation)


def scoped_facts(claim: Claim, bundle: RetrievalBundle, *, deadlines=False):
    matches = []
    field = 'deadline' if deadlines else claim.field_type
    for hit in eligible_hits(bundle):
        # Chunk positions are internal in T07. An ambiguous occurrence is not enough to prove a fact span.
        offset = hit.source.text.find(hit.text)
        if hit.source.text.find(hit.text, offset + 1) != -1:
            continue
        for fact in hit.source.facts:
            if (fact.field_type == field and scope_compatible(claim.scope, fact.scope)
                    and offset <= fact.span.start < fact.span.end <= offset + len(hit.text)):
                matches.append(FactMatch(hit, fact, fact.span.start - offset))
    return matches


def date_relation(left, right):
    if not left or not right or left.ambiguous or right.ambiguous or not left.value or not right.value:
        return None
    if left.precision == 'date':
        expected = (datetime.fromisoformat(right.value).astimezone(VN).date().isoformat()
                    if right.precision == 'datetime' else right.value)
        return 'supports' if left.value == expected else 'contradicts'
    if right.precision != 'datetime':
        return None
    return 'supports' if datetime.fromisoformat(left.value) == datetime.fromisoformat(right.value) else 'contradicts'


def fact_relation(claim: Claim, fact: SourceFact):
    left, right = claim.normalized, fact.normalized
    if claim.field_type in ('award_amount', 'payment_amount'):
        if not left.money or not right.money or left.money.basis != right.money.basis:
            return None
        return 'supports' if left.money.amount == right.money.amount else 'contradicts'
    if claim.field_type == 'deadline':
        return date_relation(left.date, right.date)
    if claim.field_type == 'application_url':
        # A notice may list several valid links. A different link never proves this link false.
        return 'supports' if left.url and normalize_url(right.url or '') == left.url else None
    if left.text and right.text:
        if folded(left.text) == folded(right.text):
            return 'supports'
        # Explicit fee negation is allowed only for the exact fee_kind in the reviewed fact scope.
        if claim.field_type == 'payment_requirement' and {folded(right.text), folded(left.text)} == {'không thu phí', 'thu phí'}:
            return 'contradicts'
    return None


def facts_conflict(matches):
    for a, b in combinations(matches, 2):
        left, right = a.fact.normalized, b.fact.normalized
        if left.money and right.money and left.money.basis == right.money.basis and left.money.amount != right.money.amount:
            return True
        if left.date and right.date and (date_relation(left.date, right.date) == 'contradicts' or
                                         date_relation(right.date, left.date) == 'contradicts'):
            return True
        if a.fact.field_type == 'payment_requirement' and {folded(left.text or ''), folded(right.text or '')} == {'thu phí', 'không thu phí'}:
            return True
    return False


def missing_fact_reason(claim, bundle):
    # Fee silence is about the matching program, not every other hit's fields.
    target = claim.scope.model_copy(update={'fee_kind': None})
    relevant = [h for h in eligible_hits(bundle) if scope_compatible(target, h.source.scope.model_copy(update={'fee_kind': None}))]
    if relevant and not any(f.field_type == claim.field_type for h in relevant for f in h.source.facts):
        return 'LINK_NOT_CONFIRMED' if claim.field_type == 'application_url' else 'SOURCE_SILENT'
    if any(f.field_type == claim.field_type for h in eligible_hits(bundle) for f in h.source.facts):
        return 'SCOPE_UNCLEAR'
    return 'LINK_NOT_CONFIRMED' if claim.field_type == 'application_url' else 'SOURCE_SILENT'


def citation_valid(ref, bundle):
    hits = [h for h in eligible_hits(bundle) if h.chunk_id == ref.chunk_id and h.version_id == ref.version_id]
    if len(hits) != 1:
        return False
    try:
        check_quote(hits[0].text, ref.quote_span, ref.quote)
        return bool(ref.quote.strip())
    except ValueError:
        return False


def cited_fact(ref, match):
    return (ref.chunk_id == match.hit.chunk_id and ref.version_id == match.hit.version_id
            and ref.quote_span.start <= match.start
            and ref.quote_span.end >= match.start + len(match.fact.quote))


def canonical_citation(ref, bundle, matches):
    """Repair literal formatting only at an exactly selected reviewed fact span."""
    if citation_valid(ref, bundle):
        return ref
    if not any(c.isalnum() for c in ref.quote):
        return ref
    for match in matches:
        exact = match.citation(ref.relation)
        if (ref.chunk_id == exact.chunk_id and ref.version_id == exact.version_id
                and ref.quote_span == exact.quote_span and ref.quote in match.hit.text
                and (ref.quote in exact.quote or exact.quote in ref.quote)
                and citation_valid(exact, bundle)):
            return exact
    return ref


EXPLANATIONS = {
    'MATCHED': 'Bằng chứng đã kiểm tra hỗ trợ trường thông tin trong phạm vi này.',
    'VALUE_MISMATCH': 'Nguồn ghi giá trị khác cho cùng trường và phạm vi.',
    'EXPLICIT_NEGATION': 'Nguồn xác nhận yêu cầu phí không tương thích với phát biểu, cùng loại và phạm vi.',
    'DEADLINE_PASSED': 'Hạn được nguồn xác nhận đã qua tại thời điểm đối chiếu.',
    'NO_SOURCE': 'Chưa có nguồn đủ điều kiện tại thời điểm đối chiếu.',
    'SOURCE_SILENT': 'Nguồn đã kiểm tra không xác nhận nội dung này; sự im lặng không chứng minh nội dung sai.',
    'SOURCE_CONFLICT': 'Các nguồn cùng phạm vi mâu thuẫn và chưa có quan hệ thay thế đủ căn cứ.',
    'SCOPE_UNCLEAR': 'Chưa khớp chương trình, năm, đối tượng hoặc loại phí.',
    'DATE_AMBIGUOUS': 'Ngày thiếu năm, có nhiều mốc hoặc chưa đủ độ chính xác để đối chiếu.',
    'INVALID_CITATION': 'Trích dẫn của bản nháp không khớp ID, phiên bản, đoạn hoặc thời điểm nguồn.',
    'LINK_NOT_CONFIRMED': 'Chưa xác nhận URL đầy đủ từ nguồn trong phạm vi đã kiểm tra.',
    'OUT_OF_SCOPE': 'Không xác minh người gửi, chủ tài khoản hoặc độ an toàn giao dịch.',
    'PARTIAL_EVIDENCE': 'Bằng chứng chưa đủ cho toàn bộ trường thông tin và đơn vị áp dụng.',
}


def validate_verdicts(drafts: list[VerdictDraft], claims: list[Claim], bundles: list[RetrievalBundle],
                      temporal: list[TemporalCheckReport], *, audit: list | None = None) -> list[ClaimVerdict]:
    by_id = join_inputs(claims, bundles, temporal)
    if len(drafts) != len(claims) or {d.claim_id for d in drafts} != set(by_id):
        raise ServiceError('PROVIDER_BAD_OUTPUT', 'Bản nháp thiếu hoặc trùng claim ID.')
    draft_map = {d.claim_id: d for d in drafts}
    reports = {t.claim_id: t for t in temporal}
    results = []
    for claim in claims:
        draft, bundle, report = draft_map[claim.claim_id], by_id[claim.claim_id], reports[claim.claim_id]
        matches = scoped_facts(claim, bundle, deadlines=claim.field_type == 'current_availability')
        aligned = [canonical_citation(e, bundle, matches) for e in draft.evidence]
        canonicalized = sum(a != e for a, e in zip(aligned, draft.evidence))
        valid = [e for e in aligned if citation_valid(e, bundle)]
        removed = len(draft.evidence) - len(valid)
        relations = [fact_relation(claim, m.fact) for m in matches]
        label = draft.label
        reason = None
        checks = ['bundle_identity']
        if canonicalized:
            checks.append('quote_canonicalized')
        if valid:
            checks += ['quote_exact', 'source_available']
        if any(cited_fact(e, m) for e in valid for m in matches):
            checks.append('scope_compatible')
        # Never print draft explanation, statement, quote or claim id into audit logs.
        if re.search(r'\b(người gửi|chủ tài khoản|số tài khoản|stk|giao dịch an toàn|chắc chắn lừa đảo|sender|account owner|account number|safe transaction)\b', folded(claim.statement)):
            reason = 'OUT_OF_SCOPE'
        elif not eligible_hits(bundle):
            reason = 'NO_SOURCE'
        elif len(valid) != len(draft.evidence):
            reason = 'INVALID_CITATION'
        elif not matches:
            reason = missing_fact_reason(claim, bundle)
        elif report.needs_more_evidence:
            reason = next((r.value for r in report.reason_codes), 'DATE_AMBIGUOUS')
        elif claim.ambiguities:
            reason = 'SCOPE_UNCLEAR' if 'FEE_KIND_MISSING' in claim.ambiguities else 'PARTIAL_EVIDENCE'
        else:
            # Conflicting facts are checked across the whole bundle, including omitted citations.
            if facts_conflict(matches):
                reason = 'SOURCE_CONFLICT'
                valid = [m.citation() for m in matches]
            elif claim.field_type == 'current_availability':
                desired = 'contradicts' if report.temporal_status == 'expired' and label == 'contradicted' else None
                # Do not infer an open application window solely from a future deadline.
                if (folded(claim.normalized.text or '') != 'còn hạn' or desired is None or
                        not any(e.relation == desired and cited_fact(e, m) for e in valid for m in matches)):
                    reason = 'PARTIAL_EVIDENCE'
            elif not any(e.relation == ('supports' if label == 'supported' else 'contradicts')
                         and relation == e.relation and cited_fact(e, match)
                         for e in valid for match, relation in zip(matches, relations)):
                reason = 'LINK_NOT_CONFIRMED' if claim.field_type == 'application_url' else 'PARTIAL_EVIDENCE'
        if reason:
            label = 'insufficient_evidence'
        if label == 'insufficient_evidence':
            reason = reason or 'PARTIAL_EVIDENCE'
            valid = [e.model_copy(update={'relation': 'context'}) for e in valid]
        else:
            reason = ('DEADLINE_PASSED' if claim.field_type == 'current_availability' else
                      'MATCHED' if label == 'supported' else
                      'EXPLICIT_NEGATION' if claim.field_type == 'payment_requirement' else 'VALUE_MISMATCH')
            checks.append('reviewed_fact_relation')
            valid = [e if any(cited_fact(e, m) and
                         ((claim.field_type == 'current_availability' and e.relation == 'contradicts') or fact_relation(claim, m.fact) == e.relation)
                         for m in matches) else e.model_copy(update={'relation': 'context'}) for e in valid]
        verdict = ClaimVerdict(claim_id=claim.claim_id, label=label, reason_codes=[reason],
            explanation=EXPLANATIONS[reason], evidence=valid, temporal_status=report.temporal_status,
            field_type=claim.field_type, statement=claim.statement, normalized=claim.normalized,
            checks_passed=list(dict.fromkeys(checks + report.checks_passed)))
        changes = [key for key in VerdictDraft.model_fields if getattr(draft, key) != getattr(verdict, key)]
        entry = {'claim_index': len(results), 'raw_prediction': draft.label.value,
                 'prediction': verdict.label.value, 'guard_changes': changes,
                 'reason_codes': [reason], 'removed_citations': removed,
                 'canonicalized_citations': canonicalized}
        if audit is not None:
            audit.append(entry)
        logger.info('verification_guard %s', entry)
        results.append(verdict)
    return results
