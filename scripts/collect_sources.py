"""Registry discovery CLI and compatibility exact-notice collector; never approves sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from backend.app.services.corpus import normalize_text

MAX_BYTES = 2 * 1024 * 1024


def check_url(url):
    p = urlsplit(url)
    if (p.scheme != 'https' or p.netloc != 'dut.udn.vn' or p.query or p.fragment
            or not re.fullmatch(r'/(?:hoidongtruong|TrangSinhvien|Phong/(?:CTSV|Taichinh))/Thongbao/id/\d+', p.path)):
        raise ValueError('Only exact official public notice paths are allowed')


def collect(entry, output: Path, client):
    url = entry['url']
    check_url(url)
    with client.stream('GET', url, follow_redirects=False) as response:
        if response.status_code != 200 or 'text/html' not in response.headers.get('content-type',''):
            raise ValueError('Public HTML unavailable; redirects and attachments are not followed')
        raw = bytearray()
        for part in response.iter_bytes(chunk_size=65536):
            raw.extend(part)
            if len(raw) > MAX_BYTES:
                raise ValueError('Source exceeds byte cap')
    soup = BeautifulSoup(bytes(raw), 'html.parser')
    content = soup.select_one(entry['selector'])
    if content is None:
        raise ValueError('Expected content selector missing')
    title = content.select_one('h2')
    title = title.get_text(' ',strip=True) if title else ''
    omitted = len(content.select('img,iframe,object,embed'))
    for tag in content.select('script,style,img,iframe,object,embed'):
        tag.decompose()
    text = normalize_text(content.get_text('\n',strip=True))
    if re.search(r'mã sinh viên|họ và tên|ngày sinh|danh sách sinh viên|số điện thoại', text, re.I):
        raise ValueError('Possible personal-data list; candidate not retained')
    identity = hashlib.sha256(url.encode()).hexdigest()[:16]
    directory = output / identity
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    (directory/'text.txt').write_text(text)
    (directory/'sanitized.html').write_text(str(content))
    receipt = dict(status='candidate_NOT_approved', url=url, title=title,
        retrieved_at=datetime.now(timezone.utc).isoformat(), available_basis='first_seen',
        family_candidate=entry['family_candidate'], domain=entry['domain'],
        transport_sha256=hashlib.sha256(raw).hexdigest(), text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        sanitized_html_sha256=hashlib.sha256(str(content).encode()).hexdigest(),
        omitted_embedded_objects=omitted, attachments_followed=0,
        human_source_reviewed=False, redistribution_license_verified=False,
        note='Retained HTML strips images/scripts/iframes; transport body not retained. No facts or approval generated. Review omitted material only if lawful and necessary; never ingest personal lists.')
    (directory/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def main():
    # Keep the reviewed exact-notice helper for existing callers. All operational
    # collection now uses registry discovery, robots, DNS pinning and checkpointing.
    from scripts.sync_sources import main as sync_main
    return sync_main()


if __name__ == '__main__':
    raise SystemExit(main())
