"""Incremental, bounded listing discovery. Candidates never enter retrieval by themselves."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone
import fcntl
from html import escape
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
from uuid import uuid4

from bs4 import BeautifulSoup

from .corpus import canonical_hash, normalize_text, sha256
from .source_authority import clean_url
from .source_fetch import FetchBlocked

PII = re.compile(r'mã\s*(?:số\s*)?(?:sinh viên|sv)|họ và tên|ngày sinh|danh sách\s*(?:sinh viên|học viên)|'
    r'số (?:điện thoại|tài khoản)|\bstk\b|[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?<!\d)(?:\+84|0)[\s.\-]*(?:\d[\s.\-]*){9,10}(?!\d)', re.I)
TOPICS = {'scholarship': re.compile(r'học bổng', re.I),
          'payment': re.compile(r'học phí|thu phí|mức thu|thu tiền|gia hạn.*phí', re.I)}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value):
    descriptor,temporary=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(descriptor,'w') as handle:
            json.dump(value,handle,ensure_ascii=False,sort_keys=True,indent=2)
            handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if Path(temporary).exists(): Path(temporary).unlink()


@contextmanager
def exclusive(directory: Path, name='sync.lock'):
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    with (directory / name).open('a') as lock:
        os.fchmod(lock.fileno(),0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('sync_busy') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def state_db(directory):
    db = sqlite3.connect(directory / 'state.sqlite3', timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('''CREATE TABLE IF NOT EXISTS notices(
        url TEXT PRIMARY KEY, authority TEXT NOT NULL, listing_url TEXT NOT NULL,
        etag TEXT, modified TEXT, text_hash TEXT, candidate_path TEXT, last_seen TEXT NOT NULL)''')
    return db


def attachment_link(url, parent_url):
    """Record only syntactically public document references; no attachment network access.

    An external attachment is never trusted independently or scheduled for fetching.
    Query parameters are not authorization, and unknown destinations are not retained.
    """
    if not parent_url:
        raise ValueError('attachment_parent_required')
    clean_url(parent_url)
    p = urlsplit(url)
    if p.scheme != 'https' or p.username or p.password or p.port or not url.isascii():
        raise ValueError('attachment_destination')
    allowed = ((p.netloc == 'drive.google.com' and re.fullmatch(r'/file/d/[A-Za-z0-9_-]+/(?:view|preview)', p.path))
               or (p.netloc == 'docs.google.com' and re.fullmatch(r'/document/d/[A-Za-z0-9_-]+/edit', p.path))
               or (p.netloc == 'dut.udn.vn' and p.path.startswith('/')))
    if not allowed or re.search(r'[\s\\%]', url) or '/.' in p.path or '//' in p.path:
        raise ValueError('attachment_destination')
    # No URL here is ever handed to the HTTP fetcher. Preserve canonical provenance only.
    return urlunsplit(('https', p.netloc, p.path, '', ''))


def parse_notice(body: bytes, authority: dict, url: str):
    soup = BeautifulSoup(body, 'html.parser')
    content = soup.select_one(authority['selector'])
    if content is None:
        raise ValueError('selector_missing')
    title_tag = content.select_one('h2')
    title = normalize_text(title_tag.get_text(' ', strip=True) if title_tag else '')
    complete_text = normalize_text(content.get_text('\n', strip=True))
    if PII.search(complete_text):
        raise ValueError('personal_data_not_retained')
    category = next((c for c in authority['categories'] if TOPICS[c].search(title)), None)
    if category is None:
        raise ValueError('publisher_category_mismatch')
    # Known 16px inline emoji are punctuation, never a policy document. Unknown
    # images (even with emoji alt text) stay unread. Do not request the image URL.
    decorative = 0
    for tag in content.select('img'):
        if (re.fullmatch(r'https://static\.xx\.fbcdn\.net/images/emoji\.php/v9/[a-z0-9]+/3/16/[a-f0-9_]+\.png',tag.get('src',''))
                and tag.get('alt') and not any(c.isalnum() for c in tag['alt'])
                and re.fullmatch(r'height:\s*16px;\s*width:\s*16px;?',tag.get('style',''))):
            decorative += 1
            tag.decompose()
    attachments, application_links, rejected = [], [], 0
    def application_link(value):
        p=urlsplit(value)
        if (p.scheme=='https' and p.netloc=='forms.gle'
                and re.fullmatch(r'/[A-Za-z0-9]+',p.path)):
            return urlunsplit(('https',p.netloc,p.path,'',''))
        return None
    for tag in content.select('img,iframe,object,embed,a[href]'):
        value = tag.get('src') or tag.get('data') or tag.get('href')
        # All document links are unresolved unless explicitly reviewed later.
        if PII.search(tag.get_text(' ',strip=True)):
            rejected += 1
            continue
        if not value or value.startswith(('#','mailto:','tel:')):
            continue
        application=application_link(value) if tag.name=='a' else None
        if application:
            application_links.append(application)
            continue
        try:
            link = attachment_link(urljoin(url, value), url)
        except ValueError:
            rejected += 1
        else:
            attachments.append({'url': link, 'parent_url': url, 'kind': tag.name, 'fetched': False})
    # Editors also paste non-clickable document URLs. They carry exactly the
    # same completeness risk as an anchor and must not silently disappear.
    known_links={row['url'] for row in attachments}
    for value in re.findall(r'https?://[^\s<>"\x27]+',complete_text):
        value=value.rstrip('.,;)')
        application=application_link(value)
        if application:
            application_links.append(application)
            continue
        try:
            link=attachment_link(value,url)
        except ValueError:
            rejected += 1
        else:
            if link not in known_links:
                attachments.append({'url':link,'parent_url':url,'kind':'text','fetched':False})
                known_links.add(link)
    # Business images can also be expressed as CSS, picture/srcset or SVG.
    # They are unresolved objects, never silently treated as complete text.
    embedded = len(content.select('img,iframe,object,embed,picture,video,audio,svg'))
    embedded += sum(bool(re.search(r'url\s*\(',tag.get('style',''),re.I)) for tag in content.select('[style]'))
    tables = len(content.select('table'))
    for tag in content.select('h2,.wd-date,.wd-notify-hot,script,style,img,iframe,object,embed'):
        tag.decompose()
    for table in content.select('table'):
        table.replace_with(table.get_text(' | ', strip=True))
    text = normalize_text(content.get_text('\n', strip=True))
    if not text.strip():
        if embedded or attachments:
            text = title  # Metadata only, incomplete; no fact is ever inferred.
        else:
            raise ValueError('content_empty')
    # Attachment/OCR completeness cannot be certified by a successful HTML request.
    reasons = ['unread_attachment'] if embedded or attachments or rejected else []
    if category == 'payment': reasons.append('payment_requires_human_review')
    if re.search(r'gia hạn|đính chính|điều chỉnh|sửa đổi', title, re.I):
        reasons.append('amendment_relationship_review')
    return dict(title=title, text=text, category=category, attachments=attachments,
                extraction_policy='html_notice_v2',
                application_links=sorted(set(application_links)), decorative_images=decorative,
                tables=tables,
                omitted_embedded_objects=embedded, rejected_attachment_links=rejected,
                review_reasons=reasons, extraction_complete=not bool(embedded or attachments or rejected))


def candidate_key(parsed):
    # Embedded documents/title can change while extracted text stays identical.
    # Retain a separate review receipt; never reuse a review of the old payload.
    return sha256(parsed['text']) + '-' + canonical_hash({k:v for k,v in parsed.items() if k!='text'})[:16]


def retain_candidate(directory, body, authority, url, listing_url, parsed, first_seen, duplicate_of=None):
    from scripts.ingest_sources import extract_html
    key = candidate_key(parsed)
    text = parsed.pop('text')
    digest = sha256(text)
    source_id = 'dut_' + sha256(url)[:16]
    path = directory / 'candidates' / source_id / key
    if path.exists():
        receipt = json.loads((path/'receipt.json').read_text())
        if receipt['text_sha256'] != digest or sha256((path/'text.txt').read_text()) != digest:
            raise ValueError('candidate_integrity')
        return path, receipt
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # Install a complete candidate directory atomically; interrupted temporary dirs are ignored.
    with tempfile.TemporaryDirectory(prefix='.candidate-', dir=path.parent) as temp:
        stage = Path(temp)
        html = '<div class="wd-content-detail">' + escape(text) + '</div>'
        (stage/'sanitized.html').write_text(html)
        (stage/'text.txt').write_text(text)
        if extract_html(stage/'sanitized.html', authority['selector']) != text:
            raise ValueError('extraction_roundtrip')
        receipt = dict(format=1, status='quarantined' if parsed['review_reasons'] else 'candidate',
            authority_id=authority['authority_id'], publisher=authority['publisher'],
            canonical_url=url, listing_url=listing_url, parent_url=None,
            source_id=source_id, version_id=source_id+'_'+digest[:16],
            first_seen=first_seen, retrieved_at=first_seen, available_at=first_seen, available_basis='first_seen',
            text_sha256=digest, transport_sha256=sha256_bytes(body),
            sanitized_html_sha256=sha256(html), duplicate_of=duplicate_of,
            trust_evidence=authority['trust_evidence'], human_source_reviewed=False,
            redistribution_license_verified=False, facts=[], supersedes_version_id=None, **parsed)
        write_json(stage/'receipt.json', receipt)
        for file in stage.iterdir(): file.chmod(0o600)
        stage.chmod(0o700)
        stage.rename(path)
    return path, receipt


def sha256_bytes(body):
    import hashlib
    return hashlib.sha256(body).hexdigest()


def _sync(registry, directory: Path, fetcher, *, dry_run=False, max_pages=6, max_notices=12,
         authority_ids=None, recheck_known=True):
    """No user text enters this interface. Budgets include trust and robots requests."""
    if not 1 <= max_pages <= 20 or not 1 <= max_notices <= 50:
        raise ValueError('discovery_limits')
    authority_ids = sorted(authority_ids if authority_ids is not None else registry.authorities)
    if not set(authority_ids) <= set(registry.authorities): raise ValueError('unknown_authority')
    from .corpus_store import private_path
    directory = private_path(directory)
    started = fetcher.clock()
    receipt = dict(run_id=str(uuid4()), started_at=stamp(), dry_run=dry_run, status='running',
        authorities_validated=[], listings_checked=0, urls_discovered=0, new_urls=0, fetched=0,
        unchanged=0, updated=0, pending=0, quarantined=0, approved=0, duplicates=0,
        rejected=[], notices=[], request_count=0, cost_usd=0)
    with exclusive(directory), closing(state_db(directory)) as db:
        seen_notices, listings, validated = {}, set(), set()
        trust_pages = {}
        for aid in authority_ids:
            authority = registry.authorities[aid]
            try:
                trust_url = authority['trust_evidence']['url']
                if trust_url not in trust_pages:
                    trust_pages[trust_url] = fetcher.get(trust_url,'trust',aid).body
                soup = BeautifulSoup(trust_pages[trust_url], 'html.parser')
                links = {urljoin(trust_url, a['href']) for a in soup.select('a[href]')}
                expected = 'https://' + authority['hostname'] + authority['trust_evidence']['linked_path']
                if expected not in links: raise ValueError('authority_link_missing')
                validated.add(aid)
                receipt['authorities_validated'].append(aid)
            except (ValueError, OSError) as exc:
                receipt['rejected'].append({'authority_id':aid,'phase':'trust','reason':safe_reason(exc)})
                continue
            queue = ['https://' + authority['hostname'] + p for p in authority['listing_paths']]
            while queue and len(listings) < max_pages:
                url = queue.pop(0)
                if url in listings: continue
                listings.add(url)
                try:
                    page = fetcher.get(url,'listing',aid)
                    receipt['listings_checked'] += 1
                    soup = BeautifulSoup(page.body,'html.parser')
                    for anchor in soup.select('a[href]'):
                        link = urljoin(url, anchor['href'])
                        try:
                            registry.check(link,'notice',aid)
                        except ValueError:
                            try: registry.check(link,'listing',aid)
                            except ValueError: continue
                            if link not in listings and link not in queue: queue.append(link)
                        else:
                            label=anchor.get_text(' ',strip=True)
                            if any(TOPICS[c].search(label) for c in authority['categories']):
                                # Page discovery is bounded before allocation, including hostile HTML.
                                if len(seen_notices) < 500:
                                    seen_notices.setdefault(link,(aid,url))
                except (ValueError,OSError) as exc:
                    receipt['rejected'].append({'url':url,'phase':'listing','reason':safe_reason(exc)})
        receipt['urls_discovered']=len(seen_notices)
        known={row['url']:row for row in db.execute('SELECT * FROM notices ORDER BY last_seen,url LIMIT 1000')}
        receipt['new_urls']=sum(url not in known for url in seen_notices)
        # Persist the discovered backlog as metadata before fetching. A later listing
        # rotation or interruption cannot erase unprocessed notice links.
        if not dry_run:
            db.executemany('INSERT OR IGNORE INTO notices VALUES(?,?,?,NULL,NULL,NULL,NULL,?)',
                [(url,aid,listing,'') for url,(aid,listing) in seen_notices.items()])
            db.commit()
        # Previously discovered notices are revisited even if no longer on the first listing page.
        if recheck_known:
            for row in db.execute('SELECT url,authority,listing_url FROM notices ORDER BY last_seen,url LIMIT 500'):
                if row['authority'] in validated:
                    seen_notices.setdefault(row['url'],(row['authority'],row['listing_url']))
        # Fair by least recently checked; new links first. No guessed IDs.
        # Interleave units and preserve listing order for new notices (normally newest
        # first). Oldest checks rotate ahead on later runs; no numeric ID guessing.
        positions={url:i for i,url in enumerate(seen_notices)}
        grouped={aid:sorted((u for u,(unit,_) in seen_notices.items() if unit==aid),
            key=lambda u:(known[u]['last_seen'] if u in known else '',positions[u])) for aid in validated}
        ordered=[urls[index] for index in range(max((len(u) for u in grouped.values()),default=0))
                 for aid,urls in sorted(grouped.items()) if index<len(urls)]
        for url in ordered[:max_notices]:
            aid,listing_url=seen_notices[url]
            old=known.get(url)
            if dry_run:
                receipt['notices'].append({'url':url,'status':'discovered_dry_run'})
                continue
            try:
                headers={}
                if old and old['candidate_path'] and (directory/old['candidate_path']/'receipt.json').exists():
                    if old['etag']: headers['If-None-Match']=old['etag']
                    if old['modified']: headers['If-Modified-Since']=old['modified']
                response=fetcher.get(url,'notice',aid,headers)
                if response.status==304:
                    if not headers: raise ValueError('unexpected_304')
                    receipt['unchanged']+=1
                    db.execute('UPDATE notices SET last_seen=? WHERE url=?',(stamp(),url))
                    db.commit()
                    receipt['notices'].append({'url':url,'status':'unchanged_304'})
                    continue
                receipt['fetched']+=1
                canonical = response.url or url
                parsed=parse_notice(response.body,registry.authorities[aid],canonical)
                digest=sha256(parsed['text'])
                prior=db.execute('SELECT url FROM notices WHERE text_hash=? AND url<>? ORDER BY url LIMIT 1',
                                 (digest,url)).fetchone()
                existing_path=directory/'candidates'/('dut_'+sha256(canonical)[:16])/candidate_key(parsed)
                first_seen=(json.loads((existing_path/'receipt.json').read_text())['first_seen']
                            if existing_path.exists() else stamp())
                path,candidate=retain_candidate(directory,response.body,registry.authorities[aid],canonical,
                    listing_url,parsed,first_seen,prior['url'] if prior else None)
                status='unchanged' if old and old['candidate_path']==str(path.relative_to(directory)) else 'updated' if old and old['candidate_path'] else 'new'
                if status=='unchanged': receipt['unchanged']+=1
                elif status=='updated': receipt['updated']+=1
                if prior: receipt['duplicates']+=1
                receipt['pending' if candidate['status']=='candidate' else 'quarantined']+=1
                db.execute('INSERT OR REPLACE INTO notices VALUES(?,?,?,?,?,?,?,?)',
                    (url,aid,listing_url,response.headers.get('etag'),response.headers.get('last-modified'),
                     digest,str(path.relative_to(directory)),stamp()))
                db.commit()  # Checkpoint every notice, not just the batch.
                receipt['notices'].append({'url':url,'status':status,'candidate_status':candidate['status'],
                    'text_sha256':digest,'candidate_path':str(path.relative_to(directory)),
                    'extraction_complete':candidate['extraction_complete'],'canonical_url':canonical,
                    'redirects':list(response.redirects)})
            except (ValueError,OSError) as exc:
                db.execute('UPDATE notices SET last_seen=? WHERE url=?',(stamp(),url))
                db.commit()
                receipt['rejected'].append({'url':url,'phase':'notice','reason':safe_reason(exc)})
        receipt.update(finished_at=stamp(),request_count=fetcher.count,
            duration_seconds=round(fetcher.clock()-started,3),http=fetcher.events)
        receipt['status']=('dry_run' if dry_run else 'partial' if receipt['rejected'] and receipt['fetched']
            else 'blocked' if receipt['rejected'] else 'success' if receipt['fetched']-receipt['unchanged']>0
            else 'no_change')
        runs=directory/'runs'; runs.mkdir(mode=0o700,exist_ok=True)
        write_json(runs/(receipt['run_id']+'.json'),receipt)
    return receipt


def safe_reason(exc):
    # Exceptions from libraries can contain response/user text. Emit closed reason codes only.
    reason=str(exc)
    return reason if re.fullmatch('[a-z0-9_]+',reason) else type(exc).__name__


def sync(registry, directory: Path, fetcher, **kwargs):
    """Persist a bounded failure receipt too, including an operator interruption."""
    try:
        return _sync(registry,directory,fetcher,**kwargs)
    except BaseException as exc:
        from .corpus_store import private_path
        try:
            directory=private_path(directory)
            runs=directory/'runs'; runs.mkdir(parents=True,mode=0o700,exist_ok=True)
            write_json(runs/(str(uuid4())+'.json'),dict(status='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                finished_at=stamp(),reason=safe_reason(exc),request_count=fetcher.count,http=fetcher.events,
                dry_run=kwargs.get('dry_run',False),approved=0,cost_usd=0))
        except (OSError,ValueError):
            pass
        raise
