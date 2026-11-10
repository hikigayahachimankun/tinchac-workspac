"""T07 uses synthetic sources and public seed probes only; never test gold."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from backend.app.models import Claim, SourceVersion
from backend.app.services.corpus import build_corpus, normalize_text, validate_corpus
from backend.app.services.retrieve import Retriever

ROOT = Path(__file__).resolve().parents[2]
AS_OF = datetime(2026, 11, 9, 14, tzinfo=timezone.utc)


def source(text='Học bổng Alpha 2026 cấp 5 triệu đồng.', **changes):
    data = json.loads((ROOT / 'data/fixtures/sources.jsonl').read_text())
    text = normalize_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    data.update(text=text, content_sha256=digest, facts=[],
                version_id='fixture_' + digest[:16], family_id='alpha',
                available_at='2026-11-01T00:00:00Z', retrieved_at='2026-11-01T00:00:00Z')
    data.update(changes)
    return SourceVersion.model_validate(data)


def claim(statement='Học bổng Alpha 2026 cấp bao nhiêu?', **changes):
    data = json.loads((ROOT / 'contracts/examples/Claim.json').read_text())
    data.update(statement=statement, scope=dict.fromkeys(data['scope']), **changes)
    return Claim.model_validate(data)


def retriever(sources, **kwargs):
    chunks, manifest = build_corpus(sources, is_fixture=True)
    return Retriever(sources, chunks, manifest, **kwargs)


def test_future_quarantine_and_expired():
    old = source(effective_to={'value':'2026-11-02', 'precision':'date',
                 'timezone':'Asia/Ho_Chi_Minh', 'raw':'02/11/2026', 'ambiguous':False})
    future = source('Học bổng Alpha tương lai', available_at='2026-12-01T00:00:00Z')
    quarantine = source('Học bổng Alpha bí mật', review_status='quarantined')
    r = retriever([old, future, quarantine])
    result = r.retrieve_claim(claim(), r.corpus_version, AS_OF)
    assert [h.version_id for h in result.hits] == [old.version_id]
    assert result.reason == 'found'
    assert r.retrieve_claim(claim(), r.corpus_version, datetime(2026,1,1,tzinfo=timezone.utc)).reason == 'no_eligible_source'


def test_empty_and_no_match():
    for sources, reason in [([], 'no_eligible_source'), ([source()], 'no_match')]:
        r = retriever(sources)
        result = r.retrieve_claim(claim('zzzzzzzzqqqqqqqq'), r.corpus_version, AS_OF)
        assert result.hits == [] and result.reason == reason


def test_hash_span_and_determinism():
    s = source('Học bổng Alpha\r\n5 triệu đồng.')
    chunks, manifest = build_corpus([s], is_fixture=True)
    assert build_corpus([s], is_fixture=True) == (chunks, manifest)
    validate_corpus([s], chunks, manifest)
    bad = chunks[0].model_copy(update={'text':'wrong'})
    with pytest.raises(ValueError):
        validate_corpus([s], [bad], manifest)
    with pytest.raises(ValueError):
        build_corpus([s.model_copy(update={'content_sha256':'0'*64})], is_fixture=True)


def test_future_and_quarantine_cannot_change_ranking_statistics():
    a, b = source('Alpha Alpha Alpha cấp học bổng.'), source('Alpha cấp học bổng Beta 2026.')
    base = retriever([a,b])
    future = source('Alpha '*1000, available_at='2026-12-01T00:00:00Z')
    quarantined = source('Alpha '*800, review_status='quarantined')
    for method in ('fts5_only','fts5_tfidf_rrf'):
        base = retriever([a,b], method=method)
        extra = retriever([future,b,quarantined,a], method=method)
        before = base.retrieve_claim(claim('Alpha'),base.corpus_version,AS_OF)
        after = extra.retrieve_claim(claim('Alpha'),extra.corpus_version,AS_OF)
        assert [(h.chunk_id,h.score) for h in before.hits] == [(h.chunk_id,h.score) for h in after.hits]


def test_same_family_versions_not_replaced_by_newest():
    old = source('Alpha hạn ngày 10/11/2026.')
    new = source('Alpha gia hạn ngày 20/11/2026.', available_at='2026-11-05T00:00:00Z',
                 supersedes_version_id=old.version_id)
    r = retriever([new,old])
    early = r.retrieve_claim(claim('Alpha'),r.corpus_version,datetime(2026,11,4,tzinfo=timezone.utc))
    assert {h.version_id for h in early.hits} == {old.version_id}
    result = r.retrieve_claim(claim('Alpha'),r.corpus_version,AS_OF)
    assert {h.version_id for h in result.hits} == {old.version_id,new.version_id}
    assert {h.source.family_id for h in result.hits} == {'alpha'}
    with pytest.raises(ValueError, match='same-family'):
        build_corpus([old, new.model_copy(update={'family_id':'other'})], is_fixture=True)


def test_equal_score_tie_is_chunk_id_and_order_is_reproducible():
    a = source('Alpha học bổng')
    b = a.model_copy(update={'version_id':'fixture_other'})
    for method in ('fts5_only', 'fts5_tfidf_rrf'):
        first, second = retriever([a,b],method=method), retriever([b,a],method=method)
        assert first.corpus_version == second.corpus_version
        one = first.retrieve_claim(claim('Alpha'), first.corpus_version, AS_OF)
        two = second.retrieve_claim(claim('Alpha'), second.corpus_version, AS_OF)
        assert one == two
        assert [h.chunk_id for h in one.hits] == sorted(h.chunk_id for h in one.hits)
        assert one.hits[0].score == pytest.approx(1/61 if method=='fts5_only' else 2/61)


def test_available_boundary_utc_and_invalid_as_of():
    s = source()
    r = retriever([s])
    at = datetime.fromisoformat('2026-11-01T07:00:00+07:00')
    assert r.retrieve_claim(claim(),r.corpus_version,at).reason == 'found'
    with pytest.raises(ValueError, match='offset'):
        r.retrieve_claim(claim(),r.corpus_version,at.replace(tzinfo=None))
    for k in (0,7,True):
        with pytest.raises(ValueError):
            r.retrieve_claim(claim(),r.corpus_version,at,k)


def test_fts5_unavailable_is_technical_error(monkeypatch):
    import sqlite3
    from backend.app.services.errors import ServiceError
    class MissingFTS:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def close(self): pass
        def execute(self,*args): raise sqlite3.OperationalError('no such module: fts5')
    r = retriever([source()])
    monkeypatch.setattr('backend.app.services.retrieve._connection', MissingFTS)
    with pytest.raises(ServiceError) as caught:
        r.retrieve_claim(claim(),r.corpus_version,AS_OF)
    assert caught.value.detail.code == 'CORPUS_UNAVAILABLE'


def test_fts_query_operators_are_plain_data():
    r = retriever([source()])
    result = r.retrieve_claim(claim('Alpha " OR NOT (NEAR(*) : { /'), r.corpus_version, AS_OF)
    assert result.reason == 'found'


def test_cache_input_time_k_version_and_mutation(monkeypatch):
    from backend.app.services.errors import ServiceError
    r = retriever([source()])
    original = r.retrieve_claim(claim(),r.corpus_version,AS_OF,public=True)
    original.hits[0].source.text = 'mutated'
    original.hits.clear()
    assert r.retrieve_claim(claim(),r.corpus_version,AS_OF,public=True).hits[0].source.text != 'mutated'
    assert len(r._cache) == 1
    r.retrieve_claim(claim(claim_id='different'),r.corpus_version,AS_OF,public=True)
    r.retrieve_claim(claim(),r.corpus_version,AS_OF,1,public=True)
    r.retrieve_claim(claim(),r.corpus_version,datetime(2026,11,8,tzinfo=timezone.utc),public=True)
    assert len(r._cache) == 4
    with pytest.raises(ServiceError):
        r.retrieve_claim(claim(), 'different-version', AS_OF, public=True)
    private = retriever([source()])
    private.retrieve_claim(claim(), private.corpus_version, AS_OF)
    assert not private._cache
    monkeypatch.setattr('backend.app.services.retrieve.time.monotonic',lambda:10**12)
    r.retrieve_claim(claim(),r.corpus_version,AS_OF,public=True)
    assert len(r._cache) == 1


def test_cache_bounded_concurrent_and_caller_cannot_mutate_snapshot():
    from concurrent.futures import ThreadPoolExecutor
    s = source()
    r = retriever([s])
    s.text = 'changed by caller'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:r.retrieve_claim(claim(),r.corpus_version,AS_OF,public=True),range(8)))
    assert all(result == results[0] for result in results)
    assert results[0].hits
    for i in range(65):
        r.retrieve_claim(claim(claim_id=f'id_{i}'),r.corpus_version,AS_OF,public=True)
    assert len(r._cache) == 64


def test_identity_detects_metadata_config_and_manifest_tampering(monkeypatch):
    from backend.app.services.corpus import RETRIEVAL_CONFIG
    s = source()
    chunks, manifest = build_corpus([s],is_fixture=True)
    _, changed = build_corpus([s.model_copy(update={'family_id':'another'})],is_fixture=True)
    assert changed['corpus_version'] != manifest['corpus_version']
    with pytest.raises(ValueError, match='identity'):
        validate_corpus([s],chunks,manifest | {'source_count':40})
    monkeypatch.setitem(RETRIEVAL_CONFIG,'top_k',4)
    _, config_changed = build_corpus([s],is_fixture=True)
    assert config_changed['corpus_version'] != manifest['corpus_version']


def test_fixture_isolation_and_duplicate_ids():
    s = source()
    with pytest.raises(ValueError, match='mixed'):
        build_corpus([s],is_fixture=False)
    with pytest.raises(ValueError, match='Duplicate'):
        build_corpus([s,s],is_fixture=True)
    with pytest.raises(ValueError, match='NFC'):
        build_corpus([s.model_copy(update={'text':'Học'})],is_fixture=True)


def test_publication_date_uses_end_of_vietnam_day():
    s = source(published_at='2026-11-01',published_precision='date',available_basis='published_verified',
               available_at='2026-11-01T00:00:00Z')
    with pytest.raises(ValueError,match='publication'):
        build_corpus([s],is_fixture=True)
    build_corpus([s.model_copy(update={'available_at':datetime.fromisoformat('2026-11-01T23:59:59.999999+07:00')})],is_fixture=True)


def test_chunking_page_spans_and_atomic_money_table():
    from backend.app.services.corpus import chunk_source
    table = 'Bảng tiền và đối tượng\n' + '\n'.join(f'Nhóm {i} | 5000000 đồng' for i in range(100))
    text = '1. Thông tin\n' + 'Alpha '*210 + '\n2. Bảng tiền\n' + table + '\n3. Hạn nộp\n20/11/2026'
    s = source(text)
    chunks = chunk_source(s)
    assert any(table in c.text for c in chunks)  # atomic oversize block is kept intact
    assert ''.join(c.text for c in chunks) == s.text
    with pytest.raises(ValueError,match='partition'):
        chunk_source(s,[{'start':1,'end':len(text),'page':1}])


def test_offline_html_pdf_and_manual_provenance(tmp_path):
    import pymupdf
    from scripts.ingest_sources import extract_html, extract_pdf, ingest
    html = tmp_path/'source.html'
    html.write_text('<div class="wd-content-detail"><h2>Menu</h2><div class="wd-date">Date</div>'
                    '<p>Học bổng<br>5 triệu</p><table><tr><td>A</td><td>5000000</td></tr></table></div>')
    assert extract_html(html,'.wd-content-detail') == 'Học bổng\n5 triệu\nA | 5000000'
    with pytest.raises(ValueError):
        extract_html(html,'.missing')
    pdf = tmp_path/'source.pdf'
    with pymupdf.open() as doc:
        for text in ('Alpha award 5000000','Deadline November 20'):
            doc.new_page().insert_text((50,50),text)
        doc.save(pdf)
    text,pages = extract_pdf(pdf)
    assert len(pages)==2 and pages[0]['page']==1 and pages[1]['end']==len(text)
    with pymupdf.open() as doc:
        doc.new_page(); doc.save(tmp_path/'blank.pdf')
    with pytest.raises(ValueError,match='manual'):
        extract_pdf(tmp_path/'blank.pdf')
    # The committed normalized snapshots rebuild without ignored raw files on a fresh checkout.
    manifest = ingest(ROOT/'data/corpus/sources.json',ROOT/'config/sources.yaml',tmp_path/'rebuilt')
    from backend.app.services.corpus import load_corpus
    sources,chunks,loaded = load_corpus(tmp_path/'rebuilt')
    assert manifest==loaded
    assert all(not s.is_fixture for s in sources)
    assert all(c.page in (1,2) for c in chunks if c.version_id in
               {s.version_id for s in sources if 'drive.google' in s.canonical_url})
    before = (tmp_path/'rebuilt/manifest.json').read_bytes()
    ingest(ROOT/'data/corpus/sources.json',ROOT/'config/sources.yaml',tmp_path/'rebuilt')
    assert before == (tmp_path/'rebuilt/manifest.json').read_bytes()


def test_register_rejects_unapproved_attachment_and_missing_manual_provenance():
    from scripts.ingest_sources import validate_register
    sources = [SourceVersion.model_validate(s) for s in json.loads((ROOT/'data/corpus/sources.json').read_text())]
    register = json.loads((ROOT/'config/sources.yaml').read_text())
    pdf = next(e for e in register['sources'] if e['ingest']['method']=='manual_pdf')
    pdf['approved_content_urls'] = []
    with pytest.raises(ValueError,match='Attachment'):
        validate_register(sources,register)
    pdf['approved_content_urls'] = [pdf['canonical_url']]
    del pdf['ingest']['manual_text']
    with pytest.raises(ValueError,match='provenance'):
        validate_register(sources,register)


def test_bad_corpus_is_error_not_nei(tmp_path):
    from backend.app.services.errors import ServiceError
    with pytest.raises(ServiceError) as caught:
        Retriever.from_directory(tmp_path)
    assert caught.value.detail.code == 'CORPUS_UNAVAILABLE'


def test_query_closes_sqlite_connection(monkeypatch):
    import sqlite3
    connections=[]
    def connect():
        db=sqlite3.connect(':memory:')
        connections.append(db)
        return db
    monkeypatch.setattr('backend.app.services.retrieve._connection',connect)
    r=retriever([source()])
    r.retrieve_claim(claim(),r.corpus_version,AS_OF)
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):
        connections[0].execute('SELECT 1')


def test_ingest_rejects_dropping_or_rewriting_stored_versions(tmp_path):
    from scripts.ingest_sources import ingest
    output=tmp_path/'corpus'
    ingest(ROOT/'data/corpus/sources.json',ROOT/'config/sources.yaml',output)
    snapshot=json.loads((ROOT/'data/corpus/sources.json').read_text())
    register=json.loads((ROOT/'config/sources.yaml').read_text())
    snapshot.pop()
    register['sources'].pop()
    incoming=tmp_path/'incoming.json'; config=tmp_path/'register.json'
    incoming.write_text(json.dumps(snapshot)); config.write_text(json.dumps(register))
    before=(output/'manifest.json').read_bytes()
    with pytest.raises(ValueError,match='existing version'):
        ingest(incoming,config,output)
    assert before==(output/'manifest.json').read_bytes()


@pytest.mark.parametrize('method',['html','pdf_text','manual_pdf'])
def test_ingest_raw_parsers_are_self_contained(tmp_path,method,monkeypatch):
    import pymupdf
    import socket
    from backend.app.services.corpus import sha256, load_corpus
    from scripts.ingest_sources import ingest, extract_pdf
    def no_network(*args,**kwargs):
        raise AssertionError('Offline corpus operations must not connect to a network')
    monkeypatch.setattr(socket,'create_connection',no_network)
    notice='https://dut.udn.vn/notice/alpha'
    canonical=notice if method=='html' else 'https://drive.google.com/file/d/approved/view'
    text='Học bổng Alpha 2026 cấp 5 triệu đồng.'
    raw=tmp_path/('source.html' if method=='html' else 'source.pdf')
    if method=='html':
        raw.write_text('<div class="main"><p>'+text+'</p></div>')
    else:
        with pymupdf.open() as doc:
            doc.new_page().insert_text((50,50),'Alpha scholarship amount 5000000')
            doc.save(raw)
        if method=='pdf_text':
            text,_=extract_pdf(raw)
    sid='dut_'+sha256(canonical)[:16]
    s=source(text,is_fixture=False,available_basis='first_seen',source_id=sid,
             version_id=sid+'_'+sha256(text)[:16],canonical_url=canonical,
             parent_url=None if method=='html' else notice)
    def receipt(path):
        return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    info={'method':method,'raw':receipt(raw),'normalized_sha256':s.content_sha256,
          'reviewed_by':'fixture-author','reviewed_on':'2026-11-01','snapshot_retrieved_at':s.retrieved_at.isoformat()}
    if method!='html':
        info['pages']=[{'start':0,'end':len(text),'page':1}]
    if method=='manual_pdf':
        manual=tmp_path/'verified.txt'; manual.write_text(text+'\n')
        info.update(manual_text=receipt(manual),notes='Synthetic, reviewed full page text.')
    config={'sources':[{'source_id':s.source_id,'version_id':s.version_id,'family_id':s.family_id,
        'canonical_url':canonical,'notice_url':notice,'notice_host':'dut.udn.vn','notice_path':'/notice/alpha',
        'review_status':'approved','content_selector':'.main','approved_content_urls':[canonical],'ingest':info}]}
    snapshot=tmp_path/'snapshot.json'; snapshot.write_text(json.dumps([s.model_dump(mode='json')]))
    register=tmp_path/'register.json'; register.write_text(json.dumps(config))
    manifest=ingest(snapshot,register,tmp_path/'output',from_raw=True,root=tmp_path)
    sources,chunks,loaded=load_corpus(tmp_path/'output')
    assert loaded==manifest and len(chunks)==1
    r=Retriever(sources,chunks,loaded)
    assert r.retrieve_claim(claim('Alpha'),r.corpus_version,AS_OF).hits
    raw.write_bytes(raw.read_bytes()+b'corrupt')
    with pytest.raises(ValueError,match='hash'):
        ingest(snapshot,register,tmp_path/'output',from_raw=True,root=tmp_path)


def test_exact_fact_cannot_be_split_by_page_boundary():
    from backend.app.models import SourceFact
    from backend.app.services.corpus import chunk_source
    s=source()
    s.facts=[SourceFact(field_type='award_amount',normalized=claim().normalized,
                       scope=s.scope,quote=s.text[5:15],span={'start':5,'end':15})]
    with pytest.raises(ValueError,match='bisects'):
        chunk_source(s,[{'start':0,'end':10,'page':1},{'start':10,'end':len(s.text),'page':2}])


def test_ten_seed_probes_replay_same_topk(tmp_path):
    from scripts.ingest_sources import ingest
    from scripts.retrieval_dev import compare
    target=tmp_path/'corpus'
    ingest(ROOT/'data/corpus/sources.json',ROOT/'config/sources.yaml',target)
    first=compare(target,ROOT/'data/dev/retrieval_seed.json')
    second=compare(target,ROOT/'data/dev/retrieval_seed.json')
    assert len(first['results'])==20
    for one,two in zip(first['results'],second['results']):
        assert one['top_k']==two['top_k'] and one['scores']==two['scores']
    assert first['summary']['fts5_tfidf_rrf']['recall_at_5']==1


def test_register_requires_exact_reviewed_supersession_evidence():
    from scripts.ingest_sources import validate_register
    sources=[SourceVersion.model_validate(s) for s in json.loads((ROOT/'data/corpus/sources.json').read_text())]
    register=json.loads((ROOT/'config/sources.yaml').read_text())
    old,new=sources[0],sources[1]
    # Synthetic relationship only: these two real notices do not actually supersede each other.
    new=new.model_copy(update={'family_id':old.family_id,'scope':old.scope,'supersedes_version_id':old.version_id})
    sources[1]=new
    entry=register['sources'][1]; entry['family_id']=old.family_id
    with pytest.raises(ValueError,match='Supersession'):
        validate_register(sources,register)
    entry['ingest']['supersession']={'version_id':old.version_id,'reviewed_by':'synthetic-test',
                                   'quote':new.text[:30]}
    validate_register(sources,register)
    build_corpus(sources,provenance=validate_register(sources,register))
    entry['ingest']['supersession']['quote']='Not present in source'
    with pytest.raises(ValueError,match='Supersession'):
        validate_register(sources,register)


def test_fact_quote_and_first_seen_cannot_be_backdated():
    s=source()
    data=s.model_dump(mode='json')
    data['facts']=[{'field_type':'award_amount','normalized':claim().normalized.model_dump(),
                   'scope':s.scope.model_dump(),'quote':'5 triệu đồng','span':{'start':0,'end':11}}]
    with pytest.raises(ValueError):
        SourceVersion.model_validate(data)
    with pytest.raises(ValueError,match='first_seen'):
        build_corpus([s.model_copy(update={'available_basis':'first_seen',
                        'available_at':datetime(2026,10,1,tzinfo=timezone.utc)})],is_fixture=True)
