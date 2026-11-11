"""Evidence-bound agent review of complete, explicitly named HTML scholarships.

This deliberately narrow parser approves program identity and one explicit initial
application deadline. It does not infer money, eligibility, supersession or rights.
All publication still goes through the existing review validator and offline ingest.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from ..models import SourceVersion, Scope, SourceFact, NormalizedValue, TextSpan
from .corpus import ROOT, canonical_hash, load_corpus, sha256
from .corpus_store import GATES, active_directory, private_path, publish_reviewed
from .normalization import date_from_raw, folded
from .source_sync import PII, exclusive, state_db, stamp, write_json

REVIEWER = 'TinChac machine review v1 (agent)'


def _fact(field, value, quote, text, scope):
    start=text.index(quote)
    if text.find(quote,start+1)!=-1:
        raise ValueError('ambiguous_quote')
    return SourceFact(field_type=field,normalized=value,scope=scope,quote=quote,
        span=TextSpan(start=start,end=start+len(quote)))


def _source(candidate, text):
    names=re.findall(r'học bổng\s+[“"]([^”"\n]{3,160})[”"]',candidate['title'],re.I)
    if len(names)!=1 or not re.search(re.escape(names[0]),text,re.I):
        raise ValueError('program_not_machine_verifiable')
    program=names[0]
    # Only explicit academic-year wording. A cohort or a deadline year does not
    # establish the academic year of every beneficiary in a multi-cohort notice.
    years=set(re.findall(r'năm học\s+(20\d{2})\s*[-–]\s*(20\d{2})',candidate['title'],re.I))
    if len(years)>1: raise ValueError('ambiguous_academic_year')
    year='-'.join(next(iter(years))) if years else None
    scope=Scope(program=program,academic_year=year,cohort=None,audience=None,fee_kind=None)
    match=re.search(re.escape(program),text,re.I)
    facts=[_fact('program',NormalizedValue(text=program,money=None,date=None,url=None),match[0],text,scope)]
    deadlines=re.findall(r'Hạn cuối nộp hồ sơ:\s*(?:hết ngày\s*)?(\d{1,2}/\d{1,2}/\d{4})\.?',text,re.I)
    if len(deadlines)==1:
        value=date_from_raw(deadlines[0])
        if not value.ambiguous:
            facts.append(_fact('deadline',NormalizedValue(text=None,money=None,date=value,url=None),deadlines[0],text,scope))
    return SourceVersion(source_id=candidate['source_id'],version_id=candidate['version_id'],
        family_id='scholarship_'+sha256(folded(program))[:16],canonical_url=candidate['canonical_url'],parent_url=None,
        title=candidate['title'],publisher=candidate['publisher'],published_at=None,published_precision='unknown',
        retrieved_at=candidate['first_seen'],available_at=candidate['first_seen'],available_basis='first_seen',
        effective_from=None,effective_to=None,supersedes_version_id=None,content_sha256=sha256(text),text=text,
        scope=scope,is_fixture=False,review_status='approved',verified_by=REVIEWER,facts=facts,
        outbound_links=candidate.get('application_links',[]))


def _notice_id(url):
    match=re.search(r'/Thongbao/id/(\d+)$',url,re.I)
    return match[1] if match else None


def review_candidates(state: Path, store: Path, registry, policy: dict, *, root=ROOT) -> dict:
    state,store=private_path(state),private_path(store)
    result=dict(started_at=stamp(),approved=[],pending=[],duplicates=[],corpus_before=None,corpus_after=None)
    with exclusive(state,'review.lock'):
        directory=active_directory(store)
        sources,_,_=load_corpus(directory) if directory else ([],[],{})
        result['corpus_before']=result['corpus_after']=directory.name if directory else None
        register=json.loads((directory/'register.json').read_text()) if directory else {'sources':[]}
        authorized=(isinstance(policy,dict) and policy.get('enabled') is True
            and policy.get('scope')=='internal_public_notices' and policy.get('redistribution') is False
            and all(isinstance(policy.get(key),str) and policy[key].strip() for key in ('confirmed_by','basis')))
        with closing(state_db(state)) as db:
            paths=[row[0] for row in db.execute('SELECT DISTINCT candidate_path FROM notices WHERE candidate_path IS NOT NULL ORDER BY candidate_path')]
        packets=[]
        for relative in paths:
            url=None
            try:
                path=(state/relative).resolve()
                if not path.is_relative_to((state/'candidates').resolve()): raise ValueError('candidate_path')
                candidate=json.loads((path/'receipt.json').read_text());url=candidate['canonical_url']
                text=(path/'text.txt').read_text()
                if sha256(text)!=candidate['text_sha256']: raise ValueError('candidate_integrity')
                if candidate['version_id'] in {s.version_id for s in sources}:
                    result['duplicates'].append(dict(url=url,reason='version_already_retained'));continue
                if any(_notice_id(s.parent_url or s.canonical_url)==_notice_id(url) for s in sources):
                    raise ValueError('existing_notice_requires_review')
                if candidate['text_sha256'] in {s.content_sha256 for s in sources}:
                    result['duplicates'].append(dict(url=url,reason='content_already_retained'));continue
                if candidate.get('extraction_policy')!='html_notice_v2':
                    raise ValueError('recollect_with_current_extractor')
                if (candidate['category']!='scholarship' or candidate['review_reasons']
                        or not candidate['extraction_complete'] or candidate['attachments']
                        or candidate['rejected_attachment_links'] or candidate['omitted_embedded_objects']):
                    raise ValueError('incomplete_or_risky')
                if PII.search(text): raise ValueError('personal_data_not_retained')
                if (candidate.get('tables',0) or re.search(
                        r'danh sách|họ tên|cccd|cmnd|căn cước|mssv|thu phí|đóng phí|chuyển tiền|nộp tiền',text,re.I)):
                    raise ValueError('privacy_or_payment_review_required')
                if re.search(r'gia hạn|đính chính|điều chỉnh|sửa đổi',text,re.I):
                    raise ValueError('amendment_relationship_review')
                authority=registry.check(url,'notice',candidate['authority_id'])
                if candidate['publisher']!=authority['publisher']: raise ValueError('publisher_mismatch')
                if not authorized: raise ValueError('content_use_confirmation_required')
                source=_source(candidate,text)
                # A matching existing programme across URLs/years can be a repost,
                # amendment or near duplicate. The agent must establish its relation.
                if any(folded(source.scope.program) in folded(s.title+' '+(s.scope.program or ''))
                       for s in sources): raise ValueError('programme_relationship_review_required')
                first=datetime.fromisoformat(candidate['first_seen'])
                if first.utcoffset() is None or first>datetime.now(timezone.utc): raise ValueError('candidate_time')
                raw=dict(path=str((path/'sanitized.html').relative_to(root)),sha256=candidate['sanitized_html_sha256'])
                entry=dict(version_id=source.version_id,source_id=source.source_id,family_id=source.family_id,
                    canonical_url=url,review_status='approved',notice_url=url,notice_host='dut.udn.vn',
                    notice_path=url.split('dut.udn.vn',1)[1],content_selector=authority['selector'],
                    approved_content_urls=[],ingest=dict(method='html',raw=raw,normalized_sha256=source.content_sha256,
                        snapshot_retrieved_at=candidate['first_seen'],reviewed_by=REVIEWER))
                evidence={
                    'authority':f"Closed registry {candidate['authority_id']}; homepage/listing provenance in candidate receipt",
                    'completeness':'HTML extractor: zero unresolved business attachments/objects/links; known inline emoji only',
                    'publisher_category':f"{authority['publisher']}; scholarship is in registered categories",
                    'personal_data':'PII code screen passed; no list/contacts retained; only public notice HTML',
                    'provenance':f"{candidate['listing_url']} -> {url}; transport SHA256 {candidate['transport_sha256']}",
                    'family':f"Explicit quoted programme {source.scope.program}; compared with {len(sources)} retained versions; no automatic supersession",
                    'facts':'Exact unique text spans; program literal in title/body; optional single explicit initial deadline parsed by date_from_raw; no inferred amounts/eligibility',
                    'temporal':f"first_seen {candidate['first_seen']}; published date unknown; no backdating",
                    'content_use':f"Internal use only; confirmation by {policy['confirmed_by']}: {policy['basis']}; policy SHA256 {canonical_hash(policy)}; no redistribution licence asserted"}
                packet=dict(version_id=source.version_id,candidate_path=relative,
                    candidate_receipt_sha256=hashlib.sha256((path/'receipt.json').read_bytes()).hexdigest(),
                    text_sha256=source.content_sha256,reviewer_identity=REVIEWER,reviewer_kind='agent',
                    gates={k:dict(passed=True,evidence=evidence[k]) for k in GATES},
                    family_review=dict(family_id=source.family_id,evidence=evidence['family']))
                # Validate each candidate before appending, so one corrupt candidate
                # does not prevent independent eligible notices from being reviewed.
                from .corpus_store import validate_reviews
                validate_reviews([source],{'sources':[entry]},[packet],state,registry,root=root)
                sources.append(source);register['sources'].append(entry);packets.append(packet)
                result['approved'].append(dict(url=url,version_id=source.version_id,family_id=source.family_id,
                    text_sha256=source.content_sha256,fields=[f.field_type.value for f in source.facts]))
            except (ValueError,KeyError,OSError,TypeError) as exc:
                from .source_sync import safe_reason
                result['pending'].append(dict(url=url,reason=safe_reason(exc)))
        if packets:
            review_dir=state/'reviews';review_dir.mkdir(mode=0o700,exist_ok=True)
            # Inputs and evidence remain private; provenance is also manifest-bound.
            snapshot=review_dir/'sources.json';config=review_dir/'register.json';reviews=review_dir/'packets.json'
            write_json(snapshot,[s.model_dump(mode='json') for s in sources]);write_json(config,register);write_json(reviews,packets)
            result['corpus_after']=publish_reviewed(store,snapshot,config,reviews,state,registry,root=root)
        result['finished_at']=stamp()
        write_json(state/'review-latest.json',result)
    return result
