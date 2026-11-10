import httpx
import pytest
from scripts.collect_sources import check_url, collect

ENTRY = {'url':'https://dut.udn.vn/hoidongtruong/Thongbao/id/11659',
         'selector':'.wd-content-detail','family_candidate':'synthetic','domain':'payment'}


@pytest.mark.parametrize('url', ['http://dut.udn.vn/hoidongtruong/Thongbao/id/1',
    'https://dut.udn.vn.evil.test/hoidongtruong/Thongbao/id/1',
    'https://sv.dut.udn.vn/login','https://dut.udn.vn/hoidongtruong/Thongbao/id/1?url=http://127.0.0.1'])
def test_non_notice_urls_are_rejected(url):
    with pytest.raises(ValueError): check_url(url)


def test_collector_never_follows_embedded_images_or_approves_source(tmp_path):
    calls=[]
    def reply(request):
        calls.append(request)
        return httpx.Response(200,headers={'content-type':'text/html'},text='''
        <div class="wd-content-detail"><h2>Public fee notice</h2><p>Deadline 12/11/2026.</p>
        <img src="data:image/png;base64,private-image"><iframe src="http://127.0.0.1"></iframe></div>''')
    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        receipt=collect(ENTRY,tmp_path,client)
    assert len(calls)==1
    assert receipt['status']=='candidate_NOT_approved'
    assert receipt['omitted_embedded_objects']==2 and receipt['attachments_followed']==0
    assert receipt['human_source_reviewed'] is False
    assert not any(b'private-image' in p.read_bytes() for p in tmp_path.rglob('*') if p.is_file())


@pytest.mark.parametrize('status,body', [(302,''),(200,'<div class="wd-content-detail">Danh sách sinh viên: Họ và tên</div>')])
def test_redirect_or_personal_lists_leave_no_snapshot(tmp_path,status,body):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(status,
        headers={'content-type':'text/html','location':'http://127.0.0.1'},text=body))) as client:
        with pytest.raises(ValueError): collect(ENTRY,tmp_path,client)
    assert not list(tmp_path.iterdir())


def test_oversized_candidate_is_rejected_before_retention(tmp_path,monkeypatch):
    monkeypatch.setattr('scripts.collect_sources.MAX_BYTES',16)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,
        headers={'content-type':'text/html'},content=b'x'*17))) as client:
        with pytest.raises(ValueError,match='byte cap'): collect(ENTRY,tmp_path,client)
    assert not list(tmp_path.iterdir())


def test_non_html_candidate_is_never_downloaded_as_attachment(tmp_path):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,
        headers={'content-type':'application/pdf'},content=b'%PDF-fixture'))) as client:
        with pytest.raises(ValueError,match='HTML unavailable'): collect(ENTRY,tmp_path,client)
    assert not list(tmp_path.iterdir())
