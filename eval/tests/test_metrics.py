"""Eight artificial outcomes, not DUT gold or model achievements."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend.app.models import EvidenceRef, TextSpan, VerdictDraft
from eval.harness import digest, zero_usage
from eval.metrics import paired_bootstrap, score
from eval.run_schema import EvalRunRow, EvidenceScore
from eval.schema import EvalCase, GoldRecord
from scripts.run_eval import fixture_inputs


def known_data():
    cases0, claims, bundles, _ = fixture_inputs()
    template=cases0[1]
    bundle=bundles[template.case_id]
    claim=claims[template.case_id]
    h=bundle.hits[0]
    ref=EvidenceRef(chunk_id=h.chunk_id,version_id=h.version_id,quote=h.text[:10],
        quote_span=TextSpan(start=0,end=10),relation='supports')
    ys=['supported','contradicted','insufficient_evidence','supported','contradicted',
        'insufficient_evidence','supported','insufficient_evidence']
    bs=['supported','supported','insufficient_evidence','insufficient_evidence',None,
        'supported','contradicted','insufficient_evidence']
    cases=[]; gold=[]; envs=[]; reviews=[]
    for i,(y,b) in enumerate(zip(ys,bs)):
        cid=f'artificial-{i}'
        c=template.model_copy(update={'case_id':cid,'family_id':'f0' if i<5 else 'f1',
                                      'domain':'payment' if i%2 else 'scholarship'})
        cases.append(c)
        gold.append(GoldRecord(case_id=cid,label=y,reason_codes=['MATCHED'],
            acceptable_evidence_sets=[] if y=='insufficient_evidence' else [[h.chunk_id]],
            reference_quotes=[] if y=='insufficient_evidence' else [ref.quote],temporal_status='unknown',
            rationale='Artificial scoring vector; not source annotation.',annotator_1='fixture-human-placeholder',
            annotator_2=None,agreement_before_adjudication=None,adjudication_note=None,
            quote_spans=[] if y=='insufficient_evidence' else [{'chunk_id':h.chunk_id,'quote':ref.quote,'span':ref.quote_span}]))
        for system,pred in [('A',b),('B',b),('C',y)]:
            draft=None if pred is None else VerdictDraft(claim_id=claim.claim_id,label=pred,
                reason_codes=['MATCHED'],explanation='Artificial outcome',
                evidence=[] if system=='A' or pred=='insufficient_evidence' else [ref],temporal_status='unknown')
            usage=zero_usage('test-model').model_copy(update={'cost_usd':.01,'attempts':1})
            row=EvalRunRow(run_id=f'known:{system}',case_id=cid,system=system,model='test-model',model_version=None,
                prompt_hash=system,corpus_version=bundle.corpus_version,config_hash='fixed',
                raw_prediction=draft,prediction=draft,guard_changes=[],technical_error='PROVIDER_TIMEOUT' if draft is None else None,
                retrieved_chunk_ids=[] if system=='A' else [h.chunk_id],usage=usage,
                stage_ms={'total':10+i,'provider':9+i},cache_mode='fresh')
            envs.append({'row':row.model_dump(mode='json'),'mode':'fresh',
                'bundle':None if system=='A' else bundle.model_dump(mode='json'),
                'bundle_hash':None if system=='A' else digest(bundle.model_dump(mode='json')),
                'accounting':{'known_subtotal_only':False}})
            if draft and system!='A':
                reviews.append(EvidenceScore(run_id=row.run_id,case_id=cid,citation_valid=True,
                    evidence_sufficient=True,nei_reason_adequate=True,reviewer_ids=['synthetic-review'],
                    comment='Artificial scoring test, not actual human evaluation'))
    return cases,gold,envs,reviews


def test_eight_cases_hand_calculation_and_all_api_errors_in_denominator():
    result=score(*known_data())
    b=result['systems']['B']
    assert b['accuracy']['value']==3/8
    assert b['macro_f1']==pytest.approx(1/3)
    assert b['technical_failure']['value']==1/8
    assert b['coverage']['value']==4/8
    assert b['answerable_resolution']['value']==1/5
    assert b['selective_error']['value']==3/4
    assert b['false_support']['value']==2/5
    assert b['false_contradiction']['value']==1/3
    assert b['ecv']['micro']['value']==3/8
    assert b['ecv']['family_macro']==pytest.approx(11/30)
    assert result['primary_c_minus_b']['delta']==pytest.approx(19/30)
    assert result['primary_c_minus_b']['ci95']==pytest.approx([.6,2/3])
    assert b['cost']['total_usd']==pytest.approx(.08)
    assert b['cost']['usd_per_success']==pytest.approx(.08/7)
    assert result['systems']['A']['ecv'] is None


def test_missing_row_is_error_and_missing_review_is_na():
    cases,gold,envs,reviews=known_data()
    envs=[e for e in envs if not(e['row']['system']=='B' and e['row']['case_id']=='artificial-4')]
    b=score(cases,gold,envs,reviews)['systems']['B']
    assert b['technical_failure']['value']==1/8
    assert b['technical_errors']=={'MISSING_ROW':1}
    assert b['cost']['total_usd'] is None
    result=score(cases,gold,envs,[])
    assert result['systems']['C']['ecv'] is None
    assert result['primary_c_minus_b']['ci95'] is None


def test_zero_denominators_and_empty_dataset():
    cases,gold,envs,reviews=known_data()
    for env in envs:
        if env['row']['prediction']:
            env['row']['prediction']['label']='insufficient_evidence'
            env['row']['prediction']['evidence']=[]
            env['row']['raw_prediction']=deepcopy(env['row']['prediction'])
    result=score(cases,gold,envs,reviews)
    b=result['systems']['B']
    assert b['selective_error']['value'] is None
    assert b['citation_validity']['value'] is None
    assert b['evidence_sufficiency']['value'] is None
    assert score([],[],[],[])['systems']['B']['accuracy']['value'] is None
    assert score([],[],[],[])['primary_c_minus_b']['families']==0


def test_retrieval_union_and_complete_alternative_sets():
    cases,gold,envs,reviews=known_data()
    for g in gold:
        if g.acceptable_evidence_sets:
            g.acceptable_evidence_sets.append(['another-chunk'])
    b=score(cases,gold,envs,reviews)['systems']['B']
    # 5 answerable cases; one failed call still retrieved its bundle before failing.
    assert b['retrieval_recall_at5']['value']==.5
    assert b['retrieval_complete_set_at5']['value']==1
    assert b['retrieval_hit_at5']['denominator']==5


def test_invalid_citation_keeps_accuracy_but_fails_ecv():
    cases,gold,envs,reviews=known_data()
    env=next(e for e in envs if e['row']['system']=='B' and e['row']['case_id']=='artificial-0')
    env['row']['prediction']['evidence'][0]['chunk_id']='fabricated'
    env['row']['raw_prediction']=deepcopy(env['row']['prediction'])
    b=score(cases,gold,envs,reviews)['systems']['B']
    assert b['accuracy']['value']==3/8
    assert b['ecv']['micro']['value']==2/8
    assert b['citation_validity']['value']==3/4


def test_unknown_accounting_and_replay_do_not_claim_zero_inference_cost():
    cases,gold,envs,reviews=known_data()
    envs[0]['accounting']['known_subtotal_only']=True
    a=score(cases,gold,envs,reviews)['systems']['A']
    assert a['cost']['total_usd'] is None
    for e in envs:
        e['mode']='replay'
        e['row']['cache_mode']='replay'
    b=score(cases,gold,envs,reviews)['systems']['B']
    assert b['cost']['usd_per_planned_case'] is None
    assert b['latency_ms'] is None


def test_paired_family_bootstrap_keeps_all_variants_and_equal_family_weights():
    pairs={'large':([0]*7,[1]*7),'small':([1],[0])}
    a=paired_bootstrap(pairs)
    assert a==paired_bootstrap(pairs)
    assert a['delta']==0  # case micro delta would be .75, which is wrong here.
    assert a['ci95']==[-1,1]
    with pytest.raises(ValueError):
        paired_bootstrap({'bad':([1],[1,0])})


def test_duplicate_mixed_run_and_bundle_drift_rejected():
    cases,gold,envs,reviews=known_data()
    with pytest.raises(ValueError,match='Duplicate'):
        score(cases,gold,envs+[envs[0]],reviews)
    changed=deepcopy(envs)
    changed[0]['row']['model']='other'
    with pytest.raises(ValueError,match='Mixed model'):
        score(cases,gold,changed,reviews)
    changed=deepcopy(envs)
    changed[1]['bundle_hash']='tampered'
    with pytest.raises(ValueError,match='Bundle identity'):
        score(cases,gold,changed,reviews)


def test_ablation_is_paired_only_on_preselected_temporal_cases():
    cases,gold,envs,reviews=known_data()
    ids={'artificial-0','artificial-1'}
    cases=[c.model_copy(update={'field_type':'deadline'}) if c.case_id in ids else c for c in cases]
    for env in list(envs):
        if env['row']['system']=='B' and env['row']['case_id'] in ids:
            clone=deepcopy(env)
            clone['row'].update(system='C_NO_TIME',run_id='known:C_NO_TIME',prompt_hash='C_NO_TIME')
            envs.append(clone)
    for review in list(reviews):
        if review.run_id=='known:B' and review.case_id in ids:
            reviews.append(review.model_copy(update={'run_id':'known:C_NO_TIME'}))
    result=score(cases,gold,envs,reviews,systems=('A','B','C','C_NO_TIME'),temporal_ids=ids)
    assert result['systems']['C_NO_TIME']['n']==2
    assert result['systems']['C']['temporal_accuracy']['denominator']==2
    assert result['temporal_ablation_c_minus_no_time']['families']==1
    assert result['temporal_ablation_c_minus_no_time']['delta']==.5
    assert result['temporal_ablation_c_minus_no_time']['degenerate_ci']
