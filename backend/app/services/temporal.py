"""Release cutoff, effective interval and deadline are different clocks."""
from datetime import datetime

from ..models import Claim, DateValue, RetrievalBundle, TemporalCheckReport
from .evidence import VN, eligible_hits, scoped_facts
from .normalization import normalize_claim


def boundary_status(value: DateValue | None, as_of: datetime, *, start=False):
    if not value or value.ambiguous or value.value is None or value.precision == 'unknown':
        return 'unknown'
    local = as_of.astimezone(VN)
    if value.precision == 'date':
        day = datetime.fromisoformat(value.value).date()
        if start:
            return 'not_yet_active' if local.date() < day else 'active'
        # A date without a time cannot prove the window is still open on that date.
        return 'expired' if local.date() > day else 'unknown' if local.date() == day else 'active'
    stamp = datetime.fromisoformat(value.value)
    return ('not_yet_active' if local < stamp else 'active') if start else ('expired' if local > stamp else 'active')


def check_claim(claim: Claim, bundle: RetrievalBundle, as_of: datetime) -> TemporalCheckReport:
    if as_of.utcoffset() is None or bundle.as_of != as_of or bundle.claim_id != claim.claim_id:
        raise ValueError('Temporal input identity mismatch')
    claim = normalize_claim(claim)
    temporal_field = claim.field_type in ('deadline', 'current_availability')
    status, reasons, checks, needs = 'not_applicable', [], ['source_release_cutoff'], False
    hits = eligible_hits(bundle)
    if not hits:
        status = 'unknown'
    elif temporal_field:
        matches = scoped_facts(claim, bundle, deadlines=True)
        dates = [m.fact.normalized.date for m in matches]
        dates = [d for d in dates if d is not None]
        if claim.field_type == 'deadline' and (not claim.normalized.date or claim.normalized.date.ambiguous):
            needs, reasons = True, ['DATE_AMBIGUOUS']
            status = 'unknown'
        elif not dates or any(d.ambiguous or d.value is None for d in dates):
            status, needs, reasons = 'unknown', True, ['DATE_AMBIGUOUS']
        else:
            states = {boundary_status(d, as_of) for d in dates}
            status = states.pop() if len(states) == 1 else 'unknown'
            checks.append('deadline_precision')
            if claim.field_type == 'current_availability' and status == 'unknown':
                needs, reasons = True, ['DATE_AMBIGUOUS']
    # Effective bounds affect applicability, not the truth of a historical deadline.
    relevant = {m.hit.version_id for m in scoped_facts(claim, bundle, deadlines=temporal_field)}
    starts = [h.source.effective_from for h in hits if h.version_id in relevant and h.source.effective_from]
    ends = [h.source.effective_to for h in hits if h.version_id in relevant and h.source.effective_to]
    if any(boundary_status(d, as_of, start=True) == 'not_yet_active' for d in starts):
        status = 'not_yet_active'
        checks.append('effective_interval')
    elif any(boundary_status(d, as_of) == 'expired' for d in ends):
        status = 'expired'
        checks.append('effective_interval')
    return TemporalCheckReport(claim_id=claim.claim_id, temporal_status=status, reason_codes=reasons,
                               checks_passed=checks, needs_more_evidence=needs)
