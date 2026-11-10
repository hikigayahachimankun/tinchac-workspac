"""One C verification invocation, then code guards and templates. Independent of HTTP fixture jobs."""
import asyncio
from datetime import datetime
import json
from pathlib import Path
from uuid import UUID

from ..models import (CheckCreate, CheckResult, Claim, ExtractionResult, RetrievalBundle,
                      RunMode, TemporalCheckReport, VerificationOutput)
from .evidence import eligible_hits, join_inputs, scoped_facts, validate_verdicts
from .errors import ServiceError
from .extract import CONTACTS, extract_claims, redact
from .normalization import normalize_claim
from .llm import GeminiAdapter
from .render import build_result, combine_usage
from .retrieve import Retriever
from .temporal import check_claim

PROMPT = Path(__file__).resolve().parents[3] / 'prompts/verify_c.txt'


def limit_bundles(bundles: list[RetrievalBundle]):
    """Round robin preserves one hit/claim first. Returned bundles are the shared B/C context."""
    selected = set()
    for rank in range(max((len(b.hits) for b in bundles), default=0)):
        for bundle in bundles:
            if rank < len(bundle.hits) and len(selected) < 6:
                hit = bundle.hits[rank]
                selected.add((hit.chunk_id, hit.version_id))
    clipped = [b.model_copy(update={'hits': [h for h in b.hits if (h.chunk_id, h.version_id) in selected]}) for b in bundles]
    return clipped, any(len(b.hits) != len(c.hits) for b, c in zip(bundles, clipped))


def context_text(claims, bundles, temporal):
    """Keep a bounded excerpt with original chunk offsets. Never change the underlying bundle.

    shortcut: send the first field fact's surrounding excerpt per hit for the small demo.
    Full snapshot stays available to the code guard; omitted text stays out of model context.
    """
    rows, scopes, scope_ids = [], [], {}
    headers, hit_ids = [], {}

    def scope_ref(scope):
        value = scope.model_dump(exclude_none=True)
        key = tuple(sorted(value.items()))
        if key not in scope_ids:
            scope_ids[key] = len(scopes)
            scopes.append(value)
        return scope_ids[key]

    for claim, bundle, report in zip(claims, bundles, temporal):
        hits = []
        matches = scoped_facts(claim, bundle, deadlines=claim.field_type == 'current_availability')
        for hit in eligible_hits(bundle):
            facts = [m for m in matches if m.hit.chunk_id == hit.chunk_id and m.hit.version_id == hit.version_id]
            # No reviewed same-field/scope fact means no evidence excerpt to send.
            # The full original bundle still drives silence/scope/conflict guards.
            if not facts:
                continue
            identity = (hit.chunk_id, hit.version_id)
            if identity not in hit_ids:
                hit_ids[identity] = len(headers)
                headers.append({'chunk_id': hit.chunk_id, 'version_id': hit.version_id,
                    'available_at': hit.source.available_at.isoformat(),
                    **{k: getattr(hit.source, k).model_dump(exclude={'raw'}) for k in ('effective_from', 'effective_to') if getattr(hit.source, k)},
                    **({'supersedes': hit.source.supersedes_version_id} if hit.source.supersedes_version_id else {})})
            position = facts[0].start if facts else 0
            offset = max(0, position - 40)
            excerpt = hit.text[offset:offset + 220] if facts else ''
            # Source text may contain contact data. Keep length/offsets when masking.
            safe = list(excerpt)
            for match in CONTACTS.finditer(excerpt):
                safe[match.start():match.end()] = '*' * (match.end() - match.start())
            hits.append({'hit': hit_ids[identity], 'offset': offset,
                         'text': ''.join(safe),
                         'facts': [{'field': m.fact.field_type.value, 'value': m.fact.normalized.model_dump(exclude_none=True, exclude={'date': {'raw'}}),
                                    'scope': scope_ref(m.fact.scope), 'q':[m.start, m.start + len(m.fact.quote)]} for m in facts
                                   if offset <= m.start and m.start + len(m.fact.quote) <= offset + len(excerpt)]})
        data = claim.model_dump(exclude={'input_span': True, 'scope': True, 'normalized': {'date': {'raw'}}},exclude_none=True)
        if data['normalized'].get('text') == data['statement']:
            data['normalized'].pop('text')  # Lossless default documented in the prompt.
        if claim.raw_value in claim.statement:
            data.pop('raw_value')
        if not data['ambiguities']:
            data.pop('ambiguities')
        data['scope'] = scope_ref(claim.scope)
        time_data = {'temporal_status': report.temporal_status.value}
        if report.needs_more_evidence:
            time_data.update(needs_more_evidence=True, reason_codes=[r.value for r in report.reason_codes])
        rows.append({'claim': data, 'hits': hits,
                     'temporal': time_data})
    # Redact untrusted text values, never opaque IDs or canonical dates/numeric values.
    # Redacting serialized JSON can corrupt a source ID that happens to contain digits.
    def safe_values(value):
        if isinstance(value, list):
            return [safe_values(item) for item in value]
        if isinstance(value, dict):
            return {key: redact(item) if key in {'statement','raw_value','url','program','audience','cohort','fee_kind'}
                    and isinstance(item,str) else safe_values(item)
                    for key,item in value.items()}
        return value
    payload = {'as_of': bundles[0].as_of.isoformat(), 'scopes': scopes, 'hits': headers, 'claims': rows}
    # Excerpt text is already masked with equal length above; structured normalized
    # text must be redacted separately without altering quote offsets.
    for row in rows:
        for normalized in [row['claim']['normalized']] + [f['value'] for h in row['hits'] for f in h['facts']]:
            if isinstance(normalized.get('text'),str):
                normalized['text'] = redact(normalized['text'])
    return json.dumps(safe_values(payload), ensure_ascii=False, separators=(',', ':'))


async def verify_claims(claims: list[Claim], bundles: list[RetrievalBundle], temporal: list[TemporalCheckReport],
                        *, llm: GeminiAdapter, stage='dev', public=False) -> VerificationOutput:
    join_inputs(claims, bundles, temporal)
    by_bundle = {b.claim_id: b for b in bundles}
    by_report = {t.claim_id: t for t in temporal}
    ordered = [by_bundle[c.claim_id] for c in claims]
    reports = [by_report[c.claim_id] for c in claims]

    def validate(output):
        if len(output.drafts) != len(claims) or {d.claim_id for d in output.drafts} != {c.claim_id for c in claims}:
            raise ValueError('Missing/duplicate draft IDs')

    text = context_text(claims, ordered, reports)
    return await llm.generate(prompt=PROMPT.read_text(), text=text, output_type=VerificationOutput,
        corpus_version=bundles[0].corpus_version, as_of=bundles[0].as_of, stage=stage,
        public=public and '[REDACTED]' not in text and '***' not in text,
        max_output_tokens=1200 if len(claims) == 1 else 2400,
        validate=validate)


async def verify_extraction(check_id: UUID, extraction: ExtractionResult, bundles: list[RetrievalBundle], *,
                            llm: GeminiAdapter, run_mode: RunMode, corpus_updated_at: datetime,
                            stage='dev', public=False, audit=None) -> CheckResult:
    claims = [normalize_claim(c) for c in extraction.claims]
    by_id = join_inputs(claims, bundles)
    if len({(h.chunk_id, h.version_id) for b in bundles for h in b.hits}) > 6:
        raise ServiceError('INPUT_TOO_LARGE', 'Context vượt 6 chunks; cần chọn shared bundle trước khi chạy.', status=413)
    reports = [check_claim(c, by_id[c.claim_id], by_id[c.claim_id].as_of) for c in claims]
    output = await verify_claims(claims, bundles, reports, llm=llm, stage=stage, public=public)
    verdicts = validate_verdicts(output.drafts, claims, bundles, reports, audit=audit)
    warnings = extraction.warnings + ['Context model dùng trích đoạn tối đa 220 ký tự quanh fact cùng scope; phần khác không gửi. Bundle gốc giữ nguyên cho guard.']
    return build_result(check_id, verdicts, bundles, bundles[0].as_of, run_mode,
                        combine_usage(extraction.usage, output.usage), warnings=warnings,
                        corpus_updated_at=corpus_updated_at)


async def run_pipeline(check_id: UUID, request: CheckCreate, *, llm: GeminiAdapter, retriever: Retriever,
                       corpus_updated_at: datetime, stage='dev', public=False, audit=None) -> CheckResult:
    extraction = await extract_claims(request, llm=llm, corpus_version=retriever.corpus_version, stage=stage, public=public)
    bundles = [await asyncio.to_thread(retriever.retrieve_claim, claim, retriever.corpus_version, request.as_of)
               for claim in extraction.claims]
    bundles, clipped = limit_bundles(bundles)
    if clipped:
        extraction = extraction.model_copy(update={'warnings': extraction.warnings + ['Context giới hạn 6 chunks; có hit bị cắt.']})
    return await verify_extraction(check_id, extraction, bundles, llm=llm, run_mode=llm.settings.app_mode,
                                  corpus_updated_at=corpus_updated_at, stage=stage, public=public, audit=audit)
