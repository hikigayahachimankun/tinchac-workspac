"""Bounded robots-aware public HTTPS fetch. Registry-validated redirects; no proxy/cookies/user URLs."""
from dataclasses import dataclass, replace
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import ipaddress
import fnmatch
import socket
import re
import ssl
import time
from urllib.parse import urlsplit, urljoin

import httpcore
import httpx

from .source_authority import AuthorityRegistry

USER_AGENT = 'TinChacSourceSync/1.0 (DUT public-notice internal research; no forms)'


class FetchBlocked(ValueError):
    """Safe machine-readable reason only; never include response body or arbitrary URLs."""


class RobotsPolicy:
    """RFC9309 core rules: combine matching groups, longest path, Allow wins ties.

    No sitemap traversal. Unknown records are ignored. Crawl-delay is an extra
    conservative policy; error responses are handled by SafeFetcher.
    """
    def __init__(self, text):
        groups, agents, rules, delays = [], [], [], []
        in_rules = False
        for line in text.splitlines():
            line = line.split('#', 1)[0].strip()
            if ':' not in line:
                continue
            key, value = (part.strip() for part in line.split(':', 1))
            key = key.lower()
            if key == 'user-agent':
                if in_rules:
                    groups.append((agents, rules, delays))
                    agents, rules, delays, in_rules = [], [], [], False
                agents.append(value.lower())
            elif agents and key in ('allow', 'disallow', 'crawl-delay'):
                in_rules = True
                if key == 'crawl-delay':
                    try:
                        delay = float(value)
                        if 0 <= delay <= 86400:
                            delays.append(delay)
                    except ValueError:
                        pass
                elif value:
                    rules.append((key == 'allow', value))
        groups.append((agents, rules, delays))
        selected = [(max((len(a) for a in aa if a != '*' and a in 'tinchacsourcesync'), default=0), rr, dd)
                    for aa, rr, dd in groups]
        best = max((row[0] for row in selected), default=0)
        if best:
            selected = [row for row in selected if row[0] == best]
        else:
            selected = [(0, rr, dd) for aa, rr, dd in groups if '*' in aa]
        self.rules = [rule for _, rr, _ in selected for rule in rr]
        self.delay = max((d for _, _, dd in selected for d in dd), default=1)

    def allows(self, url):
        path = urlsplit(url).path
        matched = []
        for allow, pattern in self.rules:
            anchor = pattern.endswith('$')
            body = pattern[:-1] if anchor else pattern
            # RFC9309 compares percent-encoded unreserved octets as their ASCII value.
            body = re.sub(r'%([0-9a-fA-F]{2})',lambda m:chr(int(m[1],16))
                if chr(int(m[1],16)) in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
                else m[0].upper(),body)
            # fnmatch's atomic wildcard translation avoids catastrophic regex backtracking.
            pattern_glob=body.replace('[','[[]').replace('?','[?]')+('' if anchor else '*')
            if fnmatch.fnmatchcase(path,pattern_glob):
                matched.append((len(body.replace('*', '').encode()), allow))
        return max(matched, default=(0, True))[1]


class PublicBackend(httpcore.SyncBackend):
    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host != 'dut.udn.vn' or port != 443:
            raise FetchBlocked('tcp_destination')
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = sorted({answer[4][0] for answer in answers})
        if not addresses or any(not ipaddress.ip_address(ip).is_global or
                ipaddress.ip_address(ip).is_multicast or ipaddress.ip_address(ip).is_reserved
                for ip in addresses):
            raise FetchBlocked('non_public_dns')
        # Numeric address removes the second hostname resolution. httpcore still supplies
        # the original DUT hostname to TLS/SNI and verifies its certificate.
        return super().connect_tcp(addresses[0], port, timeout, local_address, socket_options)


def public_client():
    transport = httpx.HTTPTransport(trust_env=False, retries=0)
    # The only private httpx adapter seam; pinned httpx/httpcore locks and regression test.
    transport._pool.close()
    transport._pool = httpcore.ConnectionPool(ssl_context=ssl.create_default_context(),
        network_backend=PublicBackend(), max_connections=1, max_keepalive_connections=0, retries=0)
    return httpx.Client(transport=transport, trust_env=False, timeout=10, follow_redirects=False)


@dataclass(frozen=True)
class FetchResult:
    status: int
    body: bytes
    headers: dict
    url: str | None = None
    redirects: tuple = ()


class SafeFetcher:
    def __init__(self, registry: AuthorityRegistry, client=None, *, max_requests=40,
                 max_bytes=2*1024*1024, max_seconds=90, sleep=time.sleep, clock=time.monotonic):
        if not 1 <= max_requests <= 100 or not 1 <= max_bytes <= 2*1024*1024 or not 1 <= max_seconds <= 300:
            raise ValueError('fetch_limits')
        self.registry = registry
        self.client = client if client is not None else public_client()
        self.max_requests, self.max_bytes, self.max_seconds = max_requests, max_bytes, max_seconds
        self.sleep, self.clock = sleep, clock
        self.started = clock()
        self.count = 0
        self.last = None
        self.robots = {}
        self.paused = False
        self.pacing = 1
        self.events = []

    def close(self):
        self.client.close()

    def _request(self, url, headers, *, robots=False):
        host = urlsplit(url).hostname
        for attempt in range(2):
            if self.paused or self.count >= self.max_requests:
                raise FetchBlocked('request_limit_or_host_paused')
            delay = max(0, self.pacing - (self.clock() - self.last)) if self.last is not None else 0
            if self.clock() + delay - self.started >= self.max_seconds:
                raise FetchBlocked('time_limit')
            self.sleep(delay)
            self.last = self.clock()
            self.count += 1
            # A fresh cookie jar prevents stateful login/tracking, even with test clients.
            self.client.cookies.clear()
            try:
                remaining = self.max_seconds - (self.clock() - self.started)
                with self.client.stream('GET', url, headers={'User-Agent': USER_AGENT,
                        'Accept': 'text/plain' if robots else 'text/html', 'Accept-Encoding':'identity', **headers},
                        timeout=min(10, remaining), follow_redirects=False) as response:
                    status = response.status_code
                    self.events.append({'host': host, 'path': urlsplit(url).path, 'status': status})
                    if status == 429 or status >= 500:
                        wait = 2.0
                        retry = response.headers.get('retry-after')
                        if retry:
                            try:
                                wait = float(retry) if retry.isdecimal() else max(0,
                                    (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
                            except (ValueError, TypeError, OverflowError):
                                wait = self.max_seconds
                        if attempt or wait > 10 or self.clock() + wait - self.started >= self.max_seconds:
                            self.paused = True
                            raise FetchBlocked('host_backoff')
                        self.sleep(max(1, wait))
                        continue
                    if 300 <= status < 400 and status != 304:
                        if robots:
                            raise FetchBlocked('robots_redirect_denied')
                        return FetchResult(status,b'',dict(response.headers))
                    if status == 304:
                        return FetchResult(status, b'', dict(response.headers))
                    if robots and status in (404, 410):
                        return FetchResult(status, b'', dict(response.headers))
                    if status != 200:
                        if status in (401, 403):
                            self.paused = True
                        raise FetchBlocked('http_' + str(status))
                    content_type = response.headers.get('content-type', '').split(';')[0].strip().lower()
                    if content_type not in ({'text/plain', 'text/html'} if robots else {'text/html'}):
                        raise FetchBlocked('content_type')
                    if response.headers.get('content-encoding','identity').lower() != 'identity':
                        raise FetchBlocked('content_encoding')
                    raw = bytearray()
                    for part in response.iter_bytes(chunk_size=16384):
                        if self.clock() - self.started >= self.max_seconds:
                            raise FetchBlocked('time_limit')
                        raw.extend(part)
                        if len(raw) > min(self.max_bytes,512*1024 if robots else self.max_bytes):
                            self.paused = True
                            raise FetchBlocked('byte_limit')
                    return FetchResult(status, bytes(raw), dict(response.headers))
            except httpx.HTTPError:
                if attempt:
                    raise FetchBlocked('network_error') from None
                if self.clock() + 2 - self.started >= self.max_seconds:
                    raise FetchBlocked('time_limit') from None
                self.sleep(2)
        raise FetchBlocked('retry_limit')

    def get(self, url, kind, authority_id=None, headers=None):
        authority = self.registry.check(url, kind, authority_id)
        authority_id = authority['authority_id']
        host = urlsplit(url).hostname
        if kind != 'robots':
            if host not in self.robots:
                response = self._request('https://' + host + '/robots.txt', {}, robots=True)
                text = response.body.decode('utf-8-sig', errors='replace')
                meaningful='\n'.join(line.split('#',1)[0].strip() for line in text.splitlines()).strip()
                if (re.search(r'<(?:!doctype|html|form)\b',text,re.I) or
                        meaningful and not re.search(r'^\s*user-agent\s*:',text,re.I|re.M)):
                    raise FetchBlocked('robots_unreadable')
                parser = RobotsPolicy(text)
                self.robots[host] = parser
            parser = self.robots[host]
            if not parser.allows(url):
                raise FetchBlocked('robots_disallow')
            self.pacing = max(1, parser.delay)
        chain=[]
        while True:
            result=self._request(url,headers or {},robots=kind=='robots')
            if not 300<=result.status<400 or result.status==304:
                return replace(result,url=url,redirects=tuple(chain))
            if len(chain)>=2 or not result.headers.get('location'):
                raise FetchBlocked('redirect_limit')
            target=urljoin(url,result.headers['location'])
            try:
                self.registry.check(target,kind,authority_id)
            except ValueError:
                raise FetchBlocked('redirect_denied') from None
            if target in chain or target==url:
                raise FetchBlocked('redirect_loop')
            # Each destination gets robots validation as well as registry and TCP checks.
            if not self.robots[host].allows(target):
                raise FetchBlocked('robots_disallow')
            chain.append(url)
            url=target
