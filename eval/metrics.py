"""Offline scoring. Fixed case denominators; no inference, no automatic human review."""
from collections import Counter, defaultdict
from statistics import mean
import random
import numpy as np

from backend.app.models import RetrievalBundle
from eval.harness import citation_is_valid, digest
from eval.run_schema import EvalRunRow, EvidenceScore

LABELS = ['supported', 'contradicted', 'insufficient_evidence']
DECISIVE = set(LABELS[:2])


def ratio(numerator, denominator, families=None):
    return {'value':numerator/denominator if denominator else None,
            'numerator':numerator, 'denominator':denominator,
            **({'families':len(set(families))} if families is not None else {})}


def paired_bootstrap(family_pairs, *, replicates=2000, seed=42, comparison="C tốt hơn B"):
    """Each value is (B case outcomes, C case outcomes), matched in case order."""
    if not family_pairs:
        return {'delta':None,'ci95':None,'families':0,'replicates':replicates,'seed':seed}
    deltas = []
    for fid in sorted(family_pairs):
        b,c = family_pairs[fid]
        if not b or len(b) != len(c):
            raise ValueError('Unpaired family observations')
        deltas.append(mean(c)-mean(b))
    rng = random.Random(seed)
    draws = [mean(rng.choices(deltas,k=len(deltas))) for _ in range(replicates)]
    ci = np.percentile(draws,[2.5,97.5]).tolist()
    return {'delta':mean(deltas), 'ci95':ci, 'families':len(deltas), 'replicates':replicates,
            'seed':seed, 'degenerate_ci':ci[0] == ci[1],
            'interpretation':f'chưa đủ bằng chứng {comparison} trong mẫu này' if ci[0] <= 0 <= ci[1] else 'pilot estimate; inspect direction and sample size'}


def unique_index(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        if k in result:
            raise ValueError('Duplicate scoring key')
        result[k] = row
    return result


def score(cases, gold, envelopes, evidence_scores, *, temporal_ids=(), systems=('A','B','C'), rate=27000):
    by_case = unique_index(cases,lambda c:c.case_id)
    gold = unique_index(gold,lambda g:g.case_id)
    if set(gold) != set(by_case):
        raise ValueError('Gold must cover exactly all planned cases')
    if any(by_case[c].field_type not in ('deadline','current_availability') for c in temporal_ids if c in by_case):
        raise ValueError('Temporal subset includes non-temporal fields')
    if set(temporal_ids)-by_case.keys():
        raise ValueError('Temporal subset outside planned cases')
    if rate <= 0:
        raise ValueError('Exchange rate must be positive')
    records = []
    env_by_key = {}
    for env in envelopes:
        row = EvalRunRow.model_validate(env['row'])
        if row.case_id not in by_case or row.system not in systems:
            raise ValueError('Unexpected row outside planned run')
        if row.system == 'C_NO_TIME' and row.case_id not in temporal_ids:
            raise ValueError('Ablation outside preselected temporal subset')
        if any(d is not None and d.claim_id != by_case[row.case_id].target_claim_id for d in (row.raw_prediction,row.prediction)):
            raise ValueError('Prediction target differs from planned claim')
        records.append(row)
        env_by_key[(row.system,row.case_id)] = env
    rows = unique_index(records,lambda r:(r.system,r.case_id))
    if len({r.model for r in records}) > 1 or len({r.config_hash for r in records}) > 1:
        raise ValueError('Mixed model/config run')
    versions = {r.model_version for r in records if r.model_version}
    if len(versions) > 1:
        raise ValueError('Model version drift: report separate runs')
    if len({e.get('mode') for e in envelopes}) > 1:
        raise ValueError('Do not mix fixture/replay/fresh')
    for system in systems:
        selected = [r for r in records if r.system == system]
        if len({r.run_id for r in selected}) > 1 or len({r.prompt_hash for r in selected}) > 1:
            raise ValueError('Mixed run IDs/prompts within system')
    reviews = unique_index(evidence_scores,lambda e:(e.run_id,e.case_id))
    row_review_keys = {(r.run_id,r.case_id) for r in records}
    if set(reviews)-row_review_keys:
        raise ValueError('Orphan evidence score')
    # The saved shared bundle is the independent citation scorer's snapshot.
    for cid in by_case:
        signatures = []
        for system in ('B','C','C_NO_TIME'):
            env = env_by_key.get((system,cid))
            if env is None:
                continue
            bundle = RetrievalBundle.model_validate(env['bundle'])
            r = rows[(system,cid)]
            if (digest(bundle.model_dump(mode='json')) != env['bundle_hash']
                    or [h.chunk_id for h in bundle.hits] != r.retrieved_chunk_ids
                    or bundle.as_of != by_case[cid].as_of or bundle.corpus_version != r.corpus_version
                    or bundle.claim_id != by_case[cid].target_claim_id):
                raise ValueError('Bundle identity/hash mismatch')
            signatures.append(env['bundle_hash'])
        if len(set(signatures)) > 1:
            raise ValueError('B/C/ablation did not share the bundle')
    result, outcomes = {}, {}
    for system in systems:
        active = [c for c in cases if system != 'C_NO_TIME' or c.case_id in temporal_ids]
        y = [gold[c.case_id].label.value for c in active]
        selected = [rows.get((system,c.case_id)) for c in active]
        p = [r.prediction.label.value if r and r.prediction else 'ERROR' for r in selected]
        fam = [c.family_id for c in active]
        correct = [a==b for a,b in zip(y,p)]
        f1s, support = {}, {}
        for label in LABELS:
            tp=sum(a==b==label for a,b in zip(y,p))
            fp=sum(a!=label and b==label for a,b in zip(y,p))
            fn=sum(a==label and b!=label for a,b in zip(y,p))
            denominator=2*tp+fp+fn
            f1s[label]=2*tp/denominator if denominator else 0
            support[label]=sum(a==label for a in y)
        decisive = [b in DECISIVE for b in p]
        errors = Counter(r.technical_error.value if r and r.technical_error else 'MISSING_ROW'
                         for r,b in zip(selected,p) if b=='ERROR')
        metrics = {'n':len(active),'families':len(set(fam)), 'accuracy':ratio(sum(correct),len(active),fam),
            'macro_f1':mean(f1s.values()) if active else None,'class_f1':f1s,'class_support':support,
            'technical_failure':ratio(sum(errors.values()),len(active),fam),'technical_errors':dict(errors),
            'coverage':ratio(sum(decisive),len(active),fam),
            'answerable_resolution':ratio(sum(ok and a in DECISIVE for ok,a in zip(correct,y)),sum(a in DECISIVE for a in y)),
            'selective_error':ratio(sum(d and not ok for d,ok in zip(decisive,correct)),sum(decisive)),
            'false_contradiction':ratio(sum(a=='supported' and b=='contradicted' for a,b in zip(y,p)),y.count('supported'))}
        for name, labels in [('false_support',set(LABELS[1:])),('false_support_on_C',{'contradicted'}),('false_support_on_N',{'insufficient_evidence'})]:
            metrics[name]=ratio(sum(a in labels and b=='supported' for a,b in zip(y,p)),sum(a in labels for a in y))
        money = [(a,b,c) for a,b,c in zip(y,p,active) if c.domain=='payment']
        metrics['payment_false_support']=ratio(sum(a in LABELS[1:] and b=='supported' for a,b,c in money),
            sum(a in LABELS[1:] for a,b,c in money),[c.family_id for a,b,c in money])
        temporal = [(c,r) for c,r in zip(active,selected) if c.case_id in temporal_ids]
        metrics['temporal_accuracy']=ratio(sum(r is not None and r.prediction is not None and
            r.prediction.temporal_status == gold[c.case_id].temporal_status for c,r in temporal),len(temporal))
        recall, hit, complete, valid_count, cite_count, suff, suff_n, ecv = [],[],[],0,0,0,0,[]
        review_missing = False
        for c,r,a,b in zip(active,selected,y,p):
            if system == 'A':
                continue
            g=gold[c.case_id]
            env=env_by_key.get((system,c.case_id))
            bundle=RetrievalBundle.model_validate(env['bundle']) if env else None
            refs=r.prediction.evidence if r and r.prediction else []
            count=sum(citation_is_valid(ref,bundle) for ref in refs) if bundle else 0
            valid_count += count
            cite_count += len(refs)
            union=set().union(*(set(s) for s in g.acceptable_evidence_sets))
            retrieved=set(r.retrieved_chunk_ids[:5]) if r else set()
            if union:
                recall.append(len(retrieved & union)/len(union))
                hit.append(bool(retrieved & union))
                complete.append(any(set(s)<=retrieved for s in g.acceptable_evidence_sets))
            review=reviews.get((r.run_id,c.case_id)) if r else None
            if r and r.prediction and review is None:
                review_missing=True
            if b in DECISIVE:
                suff_n += 1
                suff += bool(review and review.evidence_sufficient)
            ecv.append(int(a==b and review is not None and (
                review.nei_reason_adequate if a=='insufficient_evidence' else
                bool(refs) and count==len(refs) and review.citation_valid and review.evidence_sufficient)))
        metrics['citation_validity']=ratio(valid_count,cite_count) if system!='A' else None
        metrics['evidence_sufficiency']=ratio(suff,suff_n) if system!='A' and not review_missing else None
        metrics['retrieval_recall_at5']=ratio(sum(recall),len(recall)) if system!='A' else None
        metrics['retrieval_hit_at5']=ratio(sum(hit),len(hit)) if system!='A' else None
        metrics['retrieval_complete_set_at5']=ratio(sum(complete),len(complete)) if system!='A' else None
        metrics['evidence_review_complete']=None if system=='A' else not review_missing
        metrics['ecv']=None
        if system!='A' and not review_missing and active:
            grouped=defaultdict(list)
            for c,e in zip(active,ecv):
                grouped[c.family_id].append(e)
            metrics['ecv']={'family_macro':mean(mean(v) for v in grouped.values()),
                            'micro':ratio(sum(ecv),len(ecv),fam)}
            outcomes[system]={c.case_id:e for c,e in zip(active,ecv)}
        modes={env_by_key[(system,c.case_id)].get('mode') for c,r in zip(active,selected) if r}
        unknown=any(env_by_key[(system,c.case_id)].get('accounting',{}).get('known_subtotal_only',False)
                    for c,r in zip(active,selected) if r)
        missing=sum(r is None for r in selected)
        fresh=modes=={'fresh'}
        latencies=[r.stage_ms['total'] for r in selected if r and 'total' in r.stage_ms]
        metrics['latency_ms']={'p50':float(np.percentile(latencies,50)), 'p95':float(np.percentile(latencies,95)), 'n':len(latencies)} if fresh and latencies else None
        metrics['stage_latency_ms']={stage:{'p50':float(np.percentile(vals,50)),'p95':float(np.percentile(vals,95)),'n':len(vals)}
            for stage in sorted({k for r in selected if r for k in r.stage_ms})
            if fresh and (vals:=[r.stage_ms[stage] for r in selected if r and stage in r.stage_ms])}
        total=sum(float(r.usage.cost_usd) for r in selected if r)
        metrics['cost']={'known_usd':total,'total_usd':None if unknown or missing or not fresh else total,
            'usd_per_planned_case':total/len(active) if active and not unknown and not missing and fresh else None,
            'usd_per_success':total/sum(b!='ERROR' for b in p) if any(b!='ERROR' for b in p) and not unknown and not missing and fresh else None,
            'vnd_estimate':total*rate if not unknown and not missing and fresh else None,'usd_vnd_rate':rate,
            'origin_known_usd':sum(float(env_by_key[(system,c.case_id)].get('origin',{}).get('usage',{}).get('cost_usd',0)) for c,r in zip(active,selected) if r) if modes=={'replay'} else None,
            'inference_measurement':fresh,'unknown_accounting':unknown,'missing_rows':missing,
            'attempts':sum(r.usage.attempts for r in selected if r)}
        result[system]=metrics
    pairs=defaultdict(lambda:([],[]))
    if all(s in outcomes for s in ('B','C')):
        for c in cases:
            pairs[c.family_id][0].append(outcomes['B'][c.case_id])
            pairs[c.family_id][1].append(outcomes['C'][c.case_id])
    ablation_pairs=defaultdict(lambda:([],[]))
    if all(s in outcomes for s in ('C_NO_TIME','C')):
        for c in cases:
            if c.case_id in temporal_ids:
                ablation_pairs[c.family_id][0].append(outcomes['C_NO_TIME'][c.case_id])
                ablation_pairs[c.family_id][1].append(outcomes['C'][c.case_id])
    return {'systems':result,'primary_c_minus_b':paired_bootstrap(pairs),
            'temporal_ablation_c_minus_no_time':paired_bootstrap(ablation_pairs,comparison='C tốt hơn C_NO_TIME'),
            'mode':next(iter({e.get('mode') for e in envelopes}),None),
            'note':'A evidence metrics N/A. Missing review => ECV N/A. ERROR and missing rows remain in fixed denominators. Fixture/replay are not inference measurements.'}
