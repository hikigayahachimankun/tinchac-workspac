"""Synthetic-only discovery/security tests. No DUT network or model calls."""
import json
from pathlib import Path
from unittest.mock import patch

import httpcore
import httpx
import pytest

from backend.app.services.source_authority import AuthorityRegistry, clean_url
from backend.app.services.source_fetch import FetchBlocked, PublicBackend, SafeFetcher

HOST = 'https://dut.udn.vn'
LISTING = HOST + '/Phong/CTSV'
NOTICE = HOST + '/Phong/CTSV/Thongbao/id/99'


class Clock:
    def __init__(self): self.value = 0
    def __call__(self): return self.value
    def sleep(self, seconds): self.value += seconds


def fetcher(reply, **kwargs):
    timer = Clock()
    client = httpx.Client(transport=httpx.MockTransport(reply))
    return SafeFetcher(AuthorityRegistry(), client, clock=timer, sleep=timer.sleep, **kwargs)


@pytest.mark.parametrize('url', [
    'https://dut.udn.vn.evil.test/Phong/CTSV', 'https://news.dut.udn.vn/Phong/CTSV',
    'https://sv.dut.udn.vn/login', 'http://dut.udn.vn/Phong/CTSV',
    'https://dut.udn.vn/Phong/CTSV?next=http://127.0.0.1',
    'https://dut.udn.vn/Phong/CTSV?url=https://evil.test',
    'https://user@dut.udn.vn/Phong/CTSV', 'https://dut.udn.vn:443/Phong/CTSV',
    'https://dut.udn.vn/Phong/CTSV/%2e%2e', 'https://dut.udn.vn\\@evil.test/',
    'https://dυt.udn.vn/Phong/CTSV', 'https://xn--dut-9za.udn.vn/Phong/CTSV',
    'file:///etc/passwd', 'https://drive.google.com/file/d/a/view',
])
def test_authority_rejects_unsafe_destinations(url):
    registry = AuthorityRegistry()
    with pytest.raises(ValueError): registry.check(url, 'listing')


def test_registry_closed_by_unit_and_document_kind():
    r = AuthorityRegistry()
    assert r.check(LISTING, 'listing')['authority_id'] == 'dut_ctsv'
    assert r.check(NOTICE, 'notice', 'dut_ctsv')['categories'] == ['scholarship']
    assert clean_url(HOST) == HOST + '/'
    for url, kind in [(NOTICE, 'listing'), (LISTING, 'notice'),
                      (HOST+'/TrangSinhvien/Thongbao/id/12394', 'notice')]:
        with pytest.raises(ValueError): r.check(url, kind)
    with pytest.raises(ValueError): r.check(NOTICE, 'notice', 'dut_finance')


def test_dns_all_answers_public_and_tcp_pinned():
    backend = PublicBackend()
    for ip in ['127.0.0.1', '10.1.0.1', '169.254.169.254', '::1', 'fc00::1', '0.0.0.0', '224.0.0.1']:
        with patch('socket.getaddrinfo', return_value=[(2,1,6,'',(ip,443))]):
            with pytest.raises(FetchBlocked): backend.connect_tcp('dut.udn.vn',443)
    answers = [(2,1,6,'',('8.8.8.8',443)), (2,1,6,'',('127.0.0.1',443))]
    with patch('socket.getaddrinfo', return_value=answers):
        with pytest.raises(FetchBlocked): backend.connect_tcp('dut.udn.vn',443)
    with patch('socket.getaddrinfo', return_value=answers[:1]), patch.object(httpcore.SyncBackend,'connect_tcp') as tcp:
        backend.connect_tcp('dut.udn.vn',443,10)
        assert tcp.call_args.args[:2] == ('8.8.8.8',443)
    with pytest.raises(FetchBlocked): backend.connect_tcp('evil.test',443)


def test_robots_disallow_makes_no_notice_request():
    calls=[]
    def reply(r):
        calls.append(str(r.url))
        return httpx.Response(200,headers={'content-type':'text/plain'},
                              text='User-agent: *\nDisallow: /Phong/')
    f=fetcher(reply)
    with pytest.raises(FetchBlocked, match='robots'): f.get(LISTING,'listing')
    assert calls == [HOST+'/robots.txt']


@pytest.mark.parametrize('status', [301,302,307,308,401,403,500,503,429])
def test_access_errors_redirects_and_retries_are_bounded(status):
    calls=[]
    def reply(r):
        calls.append(str(r.url))
        if r.url.path == '/robots.txt': return httpx.Response(404)
        return httpx.Response(status,headers={'location':'http://169.254.169.254/latest', 'retry-after':'1'})
    f=fetcher(reply)
    with pytest.raises(FetchBlocked): f.get(LISTING,'listing')
    assert len(calls) == (3 if status in (429,500,503) else 2)
    assert all(url.startswith(HOST+'/') for url in calls)
    assert f.clock() >= 1


def test_robots_server_error_fails_closed_and_retry_after_not_shortened():
    f=fetcher(lambda r:httpx.Response(503,headers={'retry-after':'120'}))
    with pytest.raises(FetchBlocked, match='backoff'): f.get(NOTICE,'notice')
    assert f.count == 1


def test_caps_type_and_deadline_prevent_unbounded_reads():
    def reply(r):
        if r.url.path == '/robots.txt': return httpx.Response(404)
        return httpx.Response(200,headers={'content-type':'text/html'},content=b'x'*17)
    f=fetcher(reply,max_bytes=16)
    with pytest.raises(FetchBlocked,match='byte_limit'): f.get(LISTING,'listing')
    f=fetcher(reply,max_requests=1)
    with pytest.raises(FetchBlocked,match='request_limit'): f.get(LISTING,'listing')
    assert f.count==1
    f=fetcher(reply,max_seconds=1)
    with pytest.raises(FetchBlocked,match='time_limit'): f.get(LISTING,'listing')
    f=fetcher(lambda r:httpx.Response(404) if r.url.path=='/robots.txt' else
              httpx.Response(200,headers={'content-type':'application/pdf'},content=b'%PDF'))
    with pytest.raises(FetchBlocked,match='content_type'): f.get(NOTICE,'notice')


def test_robots_longest_match_wildcard_and_matching_groups():
    from backend.app.services.source_fetch import RobotsPolicy
    rules = RobotsPolicy('User-agent: *\nDisallow: /\nUser-agent: TinChacSourceSync\n'
        'Disallow: /Phong/*\nAllow: /Phong/CTSV$\nUser-agent: TinChacSourceSync\nAllow: /Phong/CTSV/Thongbao/')
    assert rules.allows(LISTING)
    assert rules.allows(NOTICE)
    assert not rules.allows(HOST+'/Phong/Taichinh')
    assert not rules.allows(LISTING+'/other')
    assert RobotsPolicy('User-agent: *\nDisallow: /Phong\nAllow: /Phong').allows(LISTING)
    assert not RobotsPolicy('User-agent: *\nDisallow: /*/CTSV$').allows(LISTING)


def test_byte_cap_stops_further_downloads():
    f=fetcher(lambda r:httpx.Response(404) if r.url.path=='/robots.txt' else
        httpx.Response(200,headers={'content-type':'text/html'},content=b'x'*17),max_bytes=16)
    with pytest.raises(FetchBlocked): f.get(LISTING,'listing')
    before=f.count
    with pytest.raises(FetchBlocked): f.get(NOTICE,'notice')
    assert f.count==before


def notice_html(text='Học bổng Alpha 2026 cấp 5 triệu đồng.', extra='', title='Học bổng Alpha 2026'):
    return '<div class="wd-content-detail"><h2>'+title+'</h2><p>'+text+'</p>'+extra+'</div>'


def site_reply(request, *, notice_body=None, listing_extra='', status=200):
    path=request.url.path
    if path=='/robots.txt': return httpx.Response(404)
    if path=='/': return httpx.Response(200,headers={'content-type':'text/html'},
        text='<a href="/Phong/CTSV">CTSV</a><a href="/Phong/Taichinh">Finance</a>')
    if path.startswith('/Phong/CTSV/Thongbao/'):
        return httpx.Response(status,headers={'content-type':'text/html','etag':'"test"'},
            text=notice_body or notice_html())
    return httpx.Response(200,headers={'content-type':'text/html'},
        text='<a href="'+NOTICE+'">Học bổng Alpha</a>'+listing_extra)


def run_sync(tmp_path, reply=None, **kwargs):
    from backend.app.services.source_sync import sync
    f=fetcher(reply or site_reply)
    return sync(AuthorityRegistry(),tmp_path,f,authority_ids=['dut_ctsv'],**kwargs)


def test_listing_pagination_url_dedup_and_incremental304(tmp_path):
    def reply(r):
        if r.url.path.startswith('/Phong/CTSV/Thongbao/') and r.headers.get('if-none-match'):
            return httpx.Response(304)
        return site_reply(r,listing_extra='<a href="/Phong/CTSV/Tintucds/gid/332/page/2">2</a>'
            '<a href="'+NOTICE+'">Học bổng Alpha duplicate</a><a href="https://evil.test/">Học bổng</a>')
    first=run_sync(tmp_path,reply)
    assert first['listings_checked']==3 and first['urls_discovered']==1
    assert first['new_urls']==1 and first['fetched']==1 and first['pending']==1 and first['approved']==0
    second=run_sync(tmp_path,reply)
    assert second['unchanged']==1 and second['fetched']==0 and second['status']=='no_change'
    assert len(list((tmp_path/'candidates').glob('*/*/receipt.json')))==1
    receipt=json.loads(next((tmp_path/'candidates').glob('*/*/receipt.json')).read_text())
    assert receipt['available_at']==receipt['first_seen']==receipt['retrieved_at']
    assert not receipt['human_source_reviewed'] and not receipt['facts'] and not receipt['supersedes_version_id']


def test_changed_content_preserves_history_and_is_idempotent(tmp_path):
    first=run_sync(tmp_path)
    second=run_sync(tmp_path,lambda r:site_reply(r,notice_body=notice_html('Học bổng Alpha gia hạn tới 30/11/2026.')))
    assert second['updated']==1
    assert len(list((tmp_path/'candidates').glob('*/*/receipt.json')))==2
    third=run_sync(tmp_path,lambda r:site_reply(r,notice_body=notice_html('Học bổng Alpha gia hạn tới 30/11/2026.')))
    assert third['unchanged']==1 and third['updated']==0
    assert first['notices'][0]['text_sha256']!=second['notices'][0]['text_sha256']


def test_dry_run_has_no_notice_download_or_candidate(tmp_path):
    result=run_sync(tmp_path,dry_run=True)
    assert result['status']=='dry_run' and result['fetched']==0
    assert not (tmp_path/'candidates').exists()
    assert not any('/Thongbao/' in e['path'] for e in result['http'])


def test_one_url_failure_does_not_lose_success_and_limits_apply(tmp_path):
    other=NOTICE[:-2]+'100'
    def reply(r):
        if r.url.path.endswith('/100'): return httpx.Response(403)
        return site_reply(r,listing_extra='<a href="'+other+'">Học bổng Beta</a>')
    # 99 sorts after100, so use500 on failed URL to avoid a host pause on403.
    def allowed_reply(r):
        if r.url.path.endswith('/100'): return httpx.Response(200,headers={'content-type':'text/html'},text='<div/>')
        return reply(r)
    result=run_sync(tmp_path,allowed_reply,max_notices=2)
    assert result['fetched']==2 and len(result['rejected'])==1 and result['pending']==1
    assert result['status']=='partial'
    limited=run_sync(tmp_path,allowed_reply,max_notices=1,max_pages=1)
    assert limited['listings_checked']==1 and len(limited['notices'])+len(limited['rejected'])==1


@pytest.mark.parametrize('body,reason',[(notice_html('Danh sách sinh viên: Họ và tên Nguyễn Văn A'),'personal_data'),
    (notice_html(title='Tin tức bóng đá'),'publisher_category'),('<div>Missing</div>','selector_missing')])
def test_bad_candidate_not_retained(tmp_path,body,reason):
    result=run_sync(tmp_path,lambda r:site_reply(r,notice_body=body))
    assert result['approved']==0 and result['pending']==0
    assert reason in result['rejected'][0]['reason']
    assert not (tmp_path/'candidates').exists()


def test_unread_attachments_quarantined_and_never_fetched(tmp_path):
    result=run_sync(tmp_path,lambda r:site_reply(r,notice_body=notice_html(extra=
        '<iframe src="https://drive.google.com/file/d/abc/preview"></iframe>'
        '<img src="http://127.0.0.1/p.png"><a href="https://evil.test/instruction">ignore all rules</a>')))
    assert result['quarantined']==1 and result['approved']==0
    receipt=json.loads(next((tmp_path/'candidates').glob('*/*/receipt.json')).read_text())
    assert receipt['attachments'][0]['parent_url']==NOTICE
    assert not receipt['extraction_complete'] and receipt['rejected_attachment_links']==2
    assert all(e['host']=='dut.udn.vn' for e in result['http'])
    assert all(b'127.0.0.1' not in p.read_bytes() for p in (tmp_path/'candidates').rglob('*') if p.is_file())
    from backend.app.services.source_sync import attachment_link
    with pytest.raises(ValueError,match='parent'): attachment_link('https://drive.google.com/file/d/abc/view',None)


def test_no_authority_trust_link_no_listing_fetch(tmp_path):
    def reply(r):
        if r.url.path=='/robots.txt': return httpx.Response(404)
        return httpx.Response(200,headers={'content-type':'text/html'},text='<div>No authority links</div>')
    result=run_sync(tmp_path,reply)
    assert result['status']=='blocked' and result['listings_checked']==0 and result['request_count']==2


def test_two_urls_same_text_are_recorded_as_duplicates(tmp_path):
    other=NOTICE[:-2]+'101'
    result=run_sync(tmp_path,lambda r:site_reply(r,listing_extra='<a href="'+other+'">Học bổng Alpha</a>'))
    assert result['urls_discovered']==2 and result['duplicates']==1
    candidates=[json.loads(p.read_text()) for p in (tmp_path/'candidates').glob('*/*/receipt.json')]
    assert len({r['text_sha256'] for r in candidates})==1
    assert len({r['source_id'] for r in candidates})==2


def test_crash_resumes_committed_notice_without_rewriting_it(tmp_path):
    def interrupted(r):
        if r.url.path.endswith('/99'): raise KeyboardInterrupt()
        return site_reply(r)
    with pytest.raises(KeyboardInterrupt): run_sync(tmp_path,interrupted)
    assert run_sync(tmp_path)['pending']==1
    before=next((tmp_path/'candidates').glob('*/*/receipt.json')).read_bytes()
    assert run_sync(tmp_path)['unchanged']==1
    assert next((tmp_path/'candidates').glob('*/*/receipt.json')).read_bytes()==before


def test_fixture_replay_cli_cannot_network(tmp_path,monkeypatch):
    from scripts.sync_sources import main
    monkeypatch.setattr('scripts.sync_sources.run_once',lambda *a,**k:pytest.fail('network called'))
    for mode in ('fixture','replay'):
        with pytest.raises(SystemExit): main(['collect','--mode',mode,'--enable','--state',str(tmp_path)])
    with pytest.raises(SystemExit): main(['collect','--mode','live','--state',str(tmp_path)])


def test_attachment_change_with_same_html_text_invalidates_review(tmp_path):
    first=run_sync(tmp_path,lambda r:site_reply(r,notice_body=notice_html(extra=
        '<iframe src="https://drive.google.com/file/d/first/preview"></iframe>')))
    second=run_sync(tmp_path,lambda r:site_reply(r,notice_body=notice_html(extra=
        '<iframe src="https://drive.google.com/file/d/second/preview"></iframe>')))
    assert second['updated']==1 and second['unchanged']==0
    assert first['notices'][0]['text_sha256']==second['notices'][0]['text_sha256']
    assert first['notices'][0]['candidate_path']!=second['notices'][0]['candidate_path']
    assert len(list((tmp_path/'candidates').glob('*/*/receipt.json')))==2


def test_compressed_response_and_html_robots_are_not_treated_as_policy():
    f=fetcher(lambda r:httpx.Response(200,headers={'content-type':'text/html'},text='<html>Blocked</html>'))
    with pytest.raises(FetchBlocked,match='robots_unreadable'): f.get(LISTING,'listing')
    import gzip
    f=fetcher(lambda r:httpx.Response(404) if r.url.path=='/robots.txt' else httpx.Response(200,
        headers={'content-type':'text/html','content-encoding':'gzip'},content=gzip.compress(b'x'*10000)))
    with pytest.raises(FetchBlocked,match='content_encoding'): f.get(LISTING,'listing')


def test_robots_crawl_delay_also_applies_to_retry():
    calls=[]
    def reply(r):
        calls.append(f.clock())
        if r.url.path=='/robots.txt': return httpx.Response(200,headers={'content-type':'text/plain'},
            text='User-agent: *\nCrawl-delay: 5')
        return httpx.Response(503) if len(calls)==2 else httpx.Response(200,headers={'content-type':'text/html'},text='ok')
    f=fetcher(reply); f.get(LISTING,'listing')
    assert calls==[0,5,10]


def test_same_authority_redirect_validated_and_canonical_deduplicated(tmp_path):
    alias='https://dut.udn.vn/Phong/Sinhvien/Thongbao/id/99'
    def reply(r):
        if r.url.path=='/Phong/Sinhvien/Thongbao/id/99':
            return httpx.Response(301,headers={'location':NOTICE})
        return site_reply(r,listing_extra='<a href="'+alias+'">Học bổng alias</a>')
    result=run_sync(tmp_path,reply)
    assert result['urls_discovered']==2
    candidates=list((tmp_path/'candidates').glob('*/*/receipt.json'))
    assert len(candidates)==1
    assert all(r['canonical_url']==NOTICE for r in result['notices'])
    f=fetcher(lambda r:httpx.Response(404) if r.url.path=='/robots.txt' else
        httpx.Response(301,headers={'location':'https://dut.udn.vn/Phong/Taichinh/Thongbao/id/99'}))
    with pytest.raises(FetchBlocked,match='redirect_denied'): f.get(NOTICE,'notice','dut_ctsv')


def test_redirect_loop_and_robots_destination_rejected():
    alias='https://dut.udn.vn/Phong/Sinhvien/Thongbao/id/99'
    f=fetcher(lambda r:httpx.Response(404) if r.url.path=='/robots.txt' else
        httpx.Response(301,headers={'location':alias if str(r.url)==NOTICE else NOTICE}))
    with pytest.raises(FetchBlocked,match='redirect_loop'): f.get(NOTICE,'notice')
    def reply(r):
        if r.url.path=='/robots.txt': return httpx.Response(200,headers={'content-type':'text/plain'},
            text='User-agent: *\nDisallow: /Phong/Sinhvien/')
        return httpx.Response(301,headers={'location':alias})
    f=fetcher(reply)
    with pytest.raises(FetchBlocked,match='robots'): f.get(NOTICE,'notice')
    assert f.count==2


def test_robots_percent_encoded_unreserved_octets():
    from backend.app.services.source_fetch import RobotsPolicy
    assert not RobotsPolicy('User-agent: *\nDisallow: /%50hong/CTSV').allows(LISTING)


def test_unfetched_backlog_survives_listing_rotation_and_failure_receipted(tmp_path):
    other=NOTICE[:-2]+'101'
    first=run_sync(tmp_path,lambda r:site_reply(r,listing_extra='<a href="'+other+'">Học bổng Beta</a>'),max_notices=1)
    assert first['new_urls']==2 and first['fetched']==1
    second=run_sync(tmp_path,max_notices=1)
    assert second['fetched']==1 and second['notices'][0]['url']==other
    def crash(r):
        if '/Thongbao/' in r.url.path: raise KeyboardInterrupt()
        return site_reply(r)
    with pytest.raises(KeyboardInterrupt): run_sync(tmp_path,crash)
    receipts=[json.loads(p.read_text()) for p in (tmp_path/'runs').glob('*.json')]
    assert any(r['status']=='interrupted' and r['request_count']>0 for r in receipts)


def test_robots_malformed_access_message_is_fail_closed():
    f=fetcher(lambda r:httpx.Response(200,headers={'content-type':'text/plain'},text='Automated access denied'))
    with pytest.raises(FetchBlocked,match='robots_unreadable'): f.get(LISTING,'listing')
