"""Narrow automatic review uses synthetic sources, not human/source attestations."""
import json
from pathlib import Path

import pytest

from backend.app.services.corpus import load_corpus
from backend.app.services.corpus_store import active_directory
from backend.app.services.source_authority import AuthorityRegistry
from backend.app.services.source_review import review_candidates
from backend.tests.test_source_sync import run_sync, site_reply, notice_html


def policy():
    return dict(enabled=True,scope='internal_public_notices',confirmed_by='synthetic-test-user',
        basis='Synthetic permission fixture; no real rights attested',redistribution=False)


def collect(root, *, extra='', title='Học bổng “Alpha Scholarship” năm học 2026-2027',
            text='Chương trình học bổng Alpha Scholarship tiếp nhận hồ sơ.\nHạn cuối nộp hồ sơ: hết ngày 15/9/2026.'):
    state=root/'state'
    result=run_sync(state,lambda r:site_reply(r,notice_body=notice_html(text,title=title,extra=extra)))
    return state,result


def test_machine_review_publishes_exact_facts_and_is_idempotent(tmp_path):
    state,collected=collect(tmp_path)
    store=tmp_path/'store'
    result=review_candidates(state,store,AuthorityRegistry(),policy(),root=tmp_path)
    assert len(result['approved'])==1 and result['corpus_after']!=result['corpus_before']
    sources,chunks,manifest=load_corpus(active_directory(store))
    source=sources[0]
    assert not source.is_fixture and source.verified_by=='TinChac machine review v1 (agent)'
    assert {f.field_type for f in source.facts}=={'program','deadline'}
    assert source.scope.program=='Alpha Scholarship' and source.scope.academic_year=='2026-2027'
    assert source.facts[1].normalized.date.value=='2026-09-15'
    assert all(source.text[f.span.start:f.span.end]==f.quote for f in source.facts)
    packet=manifest['provenance'][source.version_id]['source_sync_review']['packet']
    assert packet['reviewer_kind']=='agent' and 'human_review' not in packet
    assert packet['gates']['content_use']['passed']
    assert source.available_at.isoformat()==json.loads((state/collected['notices'][0]['candidate_path']/'receipt.json').read_text())['first_seen']
    again=review_candidates(state,store,AuthorityRegistry(),policy(),root=tmp_path)
    assert again['approved']==[] and again['corpus_after']==result['corpus_after']


@pytest.mark.parametrize('extra',[
    '<img src="https://dut.udn.vn/Files/policy.png">',
    '<iframe src="https://drive.google.com/file/d/abc/preview"></iframe>',
])
def test_unknown_business_attachment_never_auto_approved(tmp_path,extra):
    state,_=collect(tmp_path,extra=extra)
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='incomplete_or_risky'
    assert active_directory(tmp_path/'store') is None


def test_missing_content_use_authority_keeps_complete_candidate_pending(tmp_path):
    state,_=collect(tmp_path)
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),{},root=tmp_path)
    assert result['pending'][0]['reason']=='content_use_confirmation_required'
    assert active_directory(tmp_path/'store') is None


def test_amendment_and_ambiguous_program_remain_for_review(tmp_path):
    state,_=collect(tmp_path,title='Gia hạn học bổng “Alpha Scholarship” năm học 2026-2027')
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert result['pending'][0]['reason']=='incomplete_or_risky'
    state2,_=collect(tmp_path/'other',title='Học bổng Alpha và Beta')
    result=review_candidates(state2,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert result['pending'][0]['reason']=='program_not_machine_verifiable'


def test_changed_approved_notice_requires_review_instead_of_auto_replacement(tmp_path):
    state,_=collect(tmp_path)
    store=tmp_path/'store'
    first=review_candidates(state,store,AuthorityRegistry(),policy(),root=tmp_path)
    collect(tmp_path,text='Chương trình học bổng Alpha Scholarship tiếp nhận hồ sơ mới.\nHạn cuối nộp hồ sơ: hết ngày 18/9/2026.')
    result=review_candidates(state,store,AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='existing_notice_requires_review'
    assert result['corpus_after']==first['corpus_after']


def test_corrupt_text_and_forged_fact_never_pass_machine_review(tmp_path):
    state,receipt=collect(tmp_path)
    path=state/receipt['notices'][0]['candidate_path']
    (path/'text.txt').write_text('corrupt')
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='candidate_integrity'


def test_body_amendment_requires_review_even_when_heading_is_unchanged(tmp_path):
    state,_=collect(tmp_path,text='Chương trình học bổng Alpha Scholarship gia hạn.\nHạn cuối nộp hồ sơ: hết ngày 15/9/2026.')
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='amendment_relationship_review'


def test_machine_review_never_infers_money_or_subgroup_eligibility(tmp_path):
    state,_=collect(tmp_path,text='Chương trình học bổng Alpha Scholarship tiếp nhận hồ sơ.\n01 suất: năm nhất.\n03 suất: năm ba.\n40.000 Yên/suất.')
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    sources,_,_=load_corpus(active_directory(tmp_path/'store'))
    assert [f.field_type for f in sources[0].facts]==['program']


def test_old_extraction_receipt_requires_recollection(tmp_path):
    state,run=collect(tmp_path)
    path=state/run['notices'][0]['candidate_path']/'receipt.json'
    receipt=json.loads(path.read_text());receipt.pop('extraction_policy');path.write_text(json.dumps(receipt))
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='recollect_with_current_extractor'


@pytest.mark.parametrize('text',[
    'Chương trình học bổng Alpha Scholarship. Danh sách nhận: Nguyễn Văn A.',
    'Chương trình học bổng Alpha Scholarship. Sinh viên cần đóng phí đăng ký.',
])
def test_personal_lists_and_payment_demands_require_review(tmp_path,text):
    state,_=collect(tmp_path,text=text)
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),policy(),root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='privacy_or_payment_review_required'


@pytest.mark.parametrize('field',['confirmed_by','basis'])
def test_null_content_use_evidence_cannot_authorize_publication(tmp_path,field):
    state,_=collect(tmp_path)
    p=policy();p[field]=None
    result=review_candidates(state,tmp_path/'store',AuthorityRegistry(),p,root=tmp_path)
    assert not result['approved'] and result['pending'][0]['reason']=='content_use_confirmation_required'
