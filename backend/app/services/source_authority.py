"""Closed authority registry for collection, separate from reviewed source facts."""
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from .corpus import ROOT

REGISTRY = ROOT / 'config/source_authorities.json'


def clean_url(url: str) -> str:
    # Reject parser ambiguities rather than normalizing an attack into an allowed URL.
    if (not isinstance(url, str) or len(url) > 2048 or not url.isascii()
            or re.search(r'[\s\\%#]', url)):
        raise ValueError('url_syntax')
    p = urlsplit(url)
    if (p.scheme != 'https' or p.netloc != 'dut.udn.vn' or p.username or p.password
            or p.port is not None or p.query or '//' in p.path or '/.' in p.path):
        raise ValueError('url_destination')
    return urlunsplit(('https', 'dut.udn.vn', p.path or '/', '', ''))


class AuthorityRegistry:
    def __init__(self, path: Path = REGISTRY):
        data = json.loads(path.read_text())
        self.authorities = {a['authority_id']: a for a in data['authorities']}
        if not self.authorities or len(self.authorities) != len(data['authorities']):
            raise ValueError('registry_identity')
        for a in self.authorities.values():
            if (a['institution'] != 'DUT' or a['hostname'] != 'dut.udn.vn'
                    or a['review_status'] != 'project_reviewed' or not a['reviewed_by']
                    or not a['subject_authority'] or not a['trust_evidence']['provenance']
                    or not set(a['categories']) <= {'scholarship', 'payment'}):
                raise ValueError('registry_review')
            if datetime.fromisoformat(a['last_authority_validation_at']).utcoffset() is None:
                raise ValueError('registry_time')
            clean_url(a['trust_evidence']['url'])
            for path in a['listing_paths']:
                clean_url('https://' + a['hostname'] + path)
            for pattern in a['notice_patterns'] + a['pagination_patterns']:
                re.compile(pattern)

    def check(self, url: str, kind: str, authority_id: str | None = None) -> dict:
        canonical = clean_url(url)
        path = urlsplit(canonical).path
        rows = [self.authorities[authority_id]] if authority_id else self.authorities.values()
        for a in rows:
            if kind == 'robots' and path == '/robots.txt':
                return a
            if kind == 'trust' and canonical == a['trust_evidence']['url']:
                return a
            if kind == 'listing' and (path in a['listing_paths'] or
                    any(re.fullmatch(p, path) for p in a['pagination_patterns'])):
                return a
            if kind == 'notice' and any(re.fullmatch(p, path) for p in a['notice_patterns']):
                return a
        raise ValueError('outside_authority')
