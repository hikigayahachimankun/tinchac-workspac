"""Eval adapters reuse production provider/retrieval/guard; no gold imports here."""
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time

from backend.app.models import (Claim, RetrievalBundle, TemporalCheckReport, Usage,
                                VerificationOutput, VerdictDraft, check_quote)
from backend.app.services.evidence import (EXPLANATIONS, cited_fact, join_inputs, missing_fact_reason, scoped_facts,
                                          validate_verdicts)
from backend.app.services.extract import redact
from backend.app.services.normalization import folded, normalize_claim
from backend.app.services.temporal import check_claim
from eval.run_schema import EvalRunRow

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = {'A': 'baseline_a', 'B': 'baseline_b', 'C': 'verify_c', 'C_NO_TIME': 'verify_c_no_time'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_jsonl(path, model=None):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    return [model.model_validate(r) for r in rows] if model else rows


def append_jsonl(path, value):
    # O_APPEND and a single writer; each successful checkpoint is fsynced.
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, 'ab') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


def zero_usage(model='fixture-v1', provider='fixture'):
    return Usage(provider=provider, model=model, input_tokens=0, output_tokens=0, cost_usd=0,
                 cost_vnd_estimate=0, attempts=0, cache_hit=False, duration_ms=0)


def schedule(cases, temporal_ids):
    rng = random.Random(42)
    ordered = sorted(cases, key=lambda c: c.case_id)
    rng.shuffle(ordered)
    result = []
    for case in ordered:
        systems = ['A', 'B', 'C'] + (['C_NO_TIME'] if case.case_id in temporal_ids else [])
        rng.shuffle(systems)
        result.extend((case, system) for system in systems)
    return result


def prepare_claim(case, supplied=None):
    if supplied is None:
        raise ValueError('Claim sidecar required: prepare from public inputs before freeze, never gold')
    if (supplied.claim_id, supplied.statement, supplied.field_type) != (case.target_claim_id, case.target_statement, case.field_type):
        raise ValueError('Claim sidecar differs from EvalCase target')
    return normalize_claim(supplied)


def shared_bundle(claim, bundle):
    join_inputs([claim], [bundle])
    if bundle.claim_id != claim.claim_id or len(bundle.hits) > 5:
        raise ValueError('Expected same target and top5')
    # Keep a shared eligible snapshot, including superseded versions: all systems see it.
    hits = [h for h in bundle.hits if h.source.review_status == 'approved' and h.source.available_at <= bundle.as_of]
    return bundle.model_copy(deep=True, update={'hits': hits})


def static_report(claim):
    return TemporalCheckReport(claim_id=claim.claim_id, temporal_status='unknown', reason_codes=[],
                               checks_passed=['source_release_cutoff'], needs_more_evidence=False)


def no_time_guard(draft, claim, bundle):
    """Eval-local ablation. Static guards retained; no deterministic date comparison.

    Date fields rely on provider entailment after quote/scope checks. Other fields use
    the production guard with a neutral temporal report. No shared service is patched.
    """
    neutral = static_report(claim)
    # Internal static guard view only; saved/model bundle stays unchanged.
    bundle = bundle.model_copy(deep=True)
    for hit in bundle.hits:
        hit.source.effective_from = hit.source.effective_to = None
        hit.source.supersedes_version_id = None
    if claim.field_type not in ('deadline', 'current_availability'):
        guarded = validate_verdicts([draft], [claim], [bundle], [neutral])[0]
        return VerdictDraft.model_validate(guarded.model_dump(include=VerdictDraft.model_fields.keys()))
    matches = scoped_facts(claim, bundle, deadlines=True)
    refs = draft.evidence
    # Static citation checker below intentionally does not call eligible_hits (which
    # reasons about effective dates). Use exactly the cutoff-filtered shared bundle.
    valid = [e for e in refs if citation_is_valid(e, bundle)]
    reason = None
    if re.search(r'\b(người gửi|chủ tài khoản|số tài khoản|stk|giao dịch an toàn|chắc chắn lừa đảo|sender|account owner|account number|safe transaction)\b', folded(claim.statement)):
        reason = 'OUT_OF_SCOPE'
    elif not bundle.hits:
        reason = 'NO_SOURCE'
    elif len(valid) != len(refs):
        reason = 'INVALID_CITATION'
    elif not matches:
        reason = missing_fact_reason(claim,bundle)
    elif any(a != 'DATE_AMBIGUOUS' for a in claim.ambiguities):
        reason = 'PARTIAL_EVIDENCE'
    elif draft.label != 'insufficient_evidence' and not any(
            e.relation == ('supports' if draft.label == 'supported' else 'contradicts')
            and cited_fact(e, m) for e in valid for m in matches):
        reason = 'PARTIAL_EVIDENCE'
    if reason or draft.label == 'insufficient_evidence':
        return VerdictDraft.model_validate(draft.model_dump() | {'label': 'insufficient_evidence',
            'reason_codes': [reason or 'PARTIAL_EVIDENCE'],
            'explanation': EXPLANATIONS[reason or 'PARTIAL_EVIDENCE'],
            'evidence': [e.model_copy(update={'relation': 'context'}) for e in valid]})
    reason = 'MATCHED' if draft.label == 'supported' else 'VALUE_MISMATCH'
    return VerdictDraft.model_validate(draft.model_dump() | {'reason_codes':[reason], 'explanation':EXPLANATIONS[reason]})


def citation_is_valid(ref, bundle):
    hits = [h for h in bundle.hits if h.chunk_id == ref.chunk_id and h.version_id == ref.version_id
            and h.source.review_status == 'approved' and h.source.available_at <= bundle.as_of]
    if len(hits) != 1 or not ref.quote.strip():
        return False
    try:
        check_quote(hits[0].text, ref.quote_span, ref.quote)
        return True
    except ValueError:
        return False


def context(case, claim, bundle, system):
    # All B/C variants see byte-identical source information, including every fact,
    # source title/dates/scope and full retrieved chunk. No gold-derived filtering.
    data = {'input_text': case.input_text, 'target': claim.model_dump(mode='json',exclude_none=True), 'as_of': case.as_of.isoformat()}
    if system != 'A':
        data['bundle'] = bundle.model_dump(mode='json',exclude_none=True)
        data['bundle'].pop('query')  # retrieval query repeats the target; not source evidence
        data['bundle'].pop('as_of')  # identical to root as_of
    if system == 'C':
        data['code_checks'] = check_claim(claim, bundle, case.as_of).model_dump(mode='json')
    elif system == 'C_NO_TIME':
        data['code_checks'] = {'checks_passed': ['source_release_cutoff']}
    if system != 'A':
        for hit in data['bundle']['hits']:
            source = hit['source']
            source.pop('text')  # chunk text already supplied
            for key in ('retrieved_at','available_basis','content_sha256','is_fixture','review_status','verified_by'):
                source.pop(key,None)  # provenance remains in the immutable artifact, not reasoning context
    if claim.raw_value in claim.statement:
        data['target'].pop('raw_value',None)
    # Lossless scope table avoids repeating the same program/year/audience on
    # every fact. This representation is shared by all systems.
    scopes = []
    def intern(scope):
        if scope not in scopes:
            scopes.append(scope)
        return scopes.index(scope)
    data['target']['scope'] = intern(data['target']['scope'])
    for hit in data.get('bundle',{}).get('hits',[]):
        source = hit['source']
        source['scope'] = intern(source['scope'])
        for fact in source['facts']:
            fact['scope'] = intern(fact['scope'])
    data['scopes'] = scopes
    # Normalized dates retain value/precision/ambiguity/timezone; raw dates are
    # already present in claim/chunk quotes. Same compaction as production C.
    def compact_dates(value):
        if isinstance(value,dict):
            if 'precision' in value and 'timezone' in value:
                value.pop('raw',None)
            for child in value.values():
                compact_dates(child)
        elif isinstance(value,list):
            for child in value:
                compact_dates(child)
    compact_dates(data)
    return redact(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def ledger_snapshot(adapter):
    if not hasattr(adapter, 'budget'):
        return []
    with adapter.budget.db() as db:
        return [dict(r) for r in db.execute('SELECT id,created_at,metadata,state,outcome,reserved_nusd,actual_nusd,charged_nusd,input_tokens,output_tokens,model_version,provider_request_id,duration_ms FROM llm_attempts WHERE json_extract(metadata,\'$.run_id\')=?', (adapter.run_id,))]


async def infer(case, claim, bundle, system, adapter, *, batch_id, config_hash, model, mode):
    from backend.app.services.errors import ServiceError
    prompt = prompt_for(system)
    raw = prediction = None
    error = None
    usage = zero_usage(model)
    changes = []
    before = {r['id'] for r in ledger_snapshot(adapter)}
    start = time.perf_counter()
    timings = {}

    def validate(output):
        if len(output.drafts) != 1 or output.drafts[0].claim_id != claim.claim_id:
            raise ValueError('Expected exactly the target claim')
        if system == 'A' and output.drafts[0].evidence:
            raise ValueError('A has no sources; evidence must be empty')

    try:
        text = context(case, claim, bundle, system)
        timings['context'] = (time.perf_counter() - start) * 1000
        provider_start = time.perf_counter()
        generated = await adapter.generate(prompt=prompt, text=text, output_type=VerificationOutput,
            corpus_version=bundle.corpus_version, as_of=case.as_of, stage='dev' if case.split == 'dev' else 'evaluation', public=False,
            max_output_tokens=1200, validate=validate)
        validate(generated)
        usage = generated.usage
        raw = prediction = generated.drafts[0]
        timings['provider'] = (time.perf_counter() - provider_start) * 1000
        guard_start = time.perf_counter()
        if system == 'C':
            report = check_claim(claim, bundle, case.as_of)
            guarded = validate_verdicts([raw], [claim], [bundle], [report])[0]
            prediction = VerdictDraft.model_validate(guarded.model_dump(include=VerdictDraft.model_fields.keys()))
        elif system == 'C_NO_TIME':
            prediction = no_time_guard(raw, claim, bundle)
        changes = [f for f in VerdictDraft.model_fields if getattr(raw, f) != getattr(prediction, f)]
        timings['guard'] = (time.perf_counter() - guard_start) * 1000
    except ServiceError as exc:
        error = exc.detail.code
        raw = prediction = None
    except Exception:
        error = 'INTERNAL_ERROR'
        raw = prediction = None
    timings['total'] = (time.perf_counter() - start) * 1000
    attempts = [r for r in ledger_snapshot(adapter) if r['id'] not in before]
    unknown = any(r['actual_nusd'] is None for r in attempts)
    versions = {r['model_version'] for r in attempts if r['model_version']}
    if len(versions) > 1:
        error, raw, prediction = 'INTERNAL_ERROR', None, None
    if error:
        # Usage holds KNOWN subtotal only; accounting flags forbid treating it as total.
        known = [r for r in attempts if r['actual_nusd'] is not None]
        usd = sum(r['actual_nusd'] for r in known) / 1e9
        rate = adapter.settings.usd_vnd_planning_rate if hasattr(adapter, 'settings') else 27000
        usage = Usage(provider='gemini' if attempts else 'none', model=model,
            input_tokens=sum(r['input_tokens'] or 0 for r in known), output_tokens=sum(r['output_tokens'] or 0 for r in known),
            cost_usd=usd, cost_vnd_estimate=usd * rate, attempts=len(attempts), cache_hit=False,
            duration_ms=int(timings['total']))
    if raw is not None:
        raw = VerdictDraft.model_validate(raw.model_dump())
    if prediction is not None:
        prediction = VerdictDraft.model_validate(prediction.model_dump())
    row = EvalRunRow(run_id=f'{batch_id}:{system}', case_id=case.case_id, system=system, model=model,
        model_version=next(iter(versions), None) if len(versions) <= 1 else None, prompt_hash=digest(prompt), corpus_version=bundle.corpus_version,
        config_hash=config_hash, raw_prediction=raw, prediction=prediction, guard_changes=changes,
        technical_error=error, retrieved_chunk_ids=[] if system == 'A' else [h.chunk_id for h in bundle.hits],
        usage=usage, stage_ms=timings, cache_mode='fresh' if mode == 'fresh' else 'replay')
    return {'row': row.model_dump(mode='json'), 'mode': mode,
            'bundle_hash': None if system == 'A' else digest(bundle.model_dump(mode='json')),
            'bundle': None if system == 'A' else bundle.model_dump(mode='json'),
            'accounting': {'known_subtotal_only': unknown, 'attempts': attempts,
                           'charged_usd': sum(r['charged_nusd'] for r in attempts) / 1e9}}


def prompt_for(system):
    prompt = (ROOT / f'prompts/{PROMPTS[system]}.txt').read_text()
    if system in ('A','B','C_NO_TIME'):
        prompt += '\nScope numbers index root scopes.\n'
    if system == 'C':
        prompt += '\nEval: target is Claim, bundle.hits are direct objects; scope numbers index root scopes. Quote offsets start at zero in hit.text. code_checks is TemporalCheckReport.\n'
    return prompt
