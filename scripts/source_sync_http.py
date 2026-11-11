"""Record one actual local live HTTP check and verify citations/previous-result immutability.

Use public, already authorized input only. Capabilities and results stay private.
This is an operational smoke, never a benchmark or a substitute for human review.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from backend.app.models import CheckRecord
from backend.app.services.corpus_store import private_path
from backend.app.services.source_sync import write_json
from scripts.public_live_qa import check_citations


def unchanged(client, directory):
    capability=json.loads((directory/'capability.json').read_text())
    url=capability['url']
    if (not url.startswith('/api/v1/checks/') or
            url!='/api/v1/checks/'+str(UUID(url.removeprefix('/api/v1/checks/')))):
        raise ValueError('capability_path')
    saved=json.loads((directory/'record.json').read_text())
    response=client.get(capability['url'],headers=capability['headers'])
    if response.status_code!=200 or response.json()!=saved:
        raise ValueError('previous_check_changed_or_unavailable')
    return saved


def smoke(base_url, output, text, *, expected_version=None, previous=None):
    parsed=urlsplit(base_url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.username or parsed.path not in ('','/') or parsed.query:
        raise ValueError('local_http_only')
    output=private_path(output)
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    with httpx.Client(base_url=base_url,timeout=10,trust_env=False,follow_redirects=False) as client:
        health=client.get('/api/v1/health');health.raise_for_status()
        if health.json()['run_mode']!='live' or not health.json()['provider_configured']:
            raise ValueError('configured_live_required')
        old=unchanged(client,previous) if previous else None
        response=client.post('/api/v1/checks',json=dict(schema_version='1.0',input_mode='text',
            confirmed_text=text,asset_id=None,asset_token=None,as_of=datetime.now(timezone.utc).isoformat(),consent_to_process=True))
        if response.status_code!=202: raise ValueError('check_not_accepted')
        created=response.json()
        capability=dict(url='/api/v1/checks/'+created['check']['check_id'],headers={'X-Resource-Token':created['access_token']})
        write_json(output/'capability.json',capability)
        for _ in range(150):
            response=client.get(capability['url'],headers=capability['headers']);response.raise_for_status()
            record=CheckRecord.model_validate(response.json())
            if record.status in ('completed','failed'): break
            time.sleep(1)
        write_json(output/'record.json',record.model_dump(mode='json'))
        citations=check_citations(client,record.result) if record.result else 0
        result=record.result
        cited={e.version_id for c in result.claims for e in c.evidence} if result else set()
        passed=record.status=='completed' and (expected_version is None or
            any(c.label=='supported' and any(e.version_id==expected_version and e.relation=='supports'
                for e in c.evidence) for c in result.claims))
        if old:
            unchanged(client,previous)
            if expected_version and old['result'] and result and old['result']['corpus_version']==result.corpus_version:
                passed=False
        summary=dict(kind='actual_live_local_HTTP_NOT_benchmark',status=record.status.value,passed=passed,
            corpus_version=result.corpus_version if result else None,
            labels=[c.label.value for c in result.claims] if result else [],
            checked_citations=citations,source_versions=sorted(cited),
            previous_result_unchanged=bool(old),error=record.error.model_dump(mode='json') if record.error else None,
            usage=result.usage.model_dump(mode='json') if result else None)
        write_json(output/'summary.json',summary)
        return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--output',type=Path,required=True,help='New private directory; never overwrite a smoke')
    parser.add_argument('--text',required=True,help='Public input only, with permission to process')
    parser.add_argument('--expected-version')
    parser.add_argument('--previous',type=Path)
    args=parser.parse_args(argv)
    summary=smoke(args.base_url,args.output,args.text,expected_version=args.expected_version,previous=args.previous)
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return 0 if summary['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
