"""HTTP smoke for the packaged fixture server. No provider or arbitrary URL fetch."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
from urllib.parse import urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]


def smoke(base_url: str) -> dict:
    parsed = urlparse(base_url)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.scheme != 'http':
        raise ValueError('Smoke is limited to a local HTTP demo server')
    results = []
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        health = client.get('/api/v1/health')
        assert health.status_code == 200
        assert health.json()['run_mode'] == 'fixture'
        assert health.json()['schema_version'] == '1.0'
        assert health.json()['corpus_version'] == 'fixture-v1'
        assert not health.json()['provider_configured']
        index = client.get('/')
        assert index.status_code == 200 and 'text/html' in index.headers['content-type']
        assert client.get('/check/demo').content == index.content
        import re
        assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', index.text)
        assert assets
        for path in assets:
            assert client.get(path).status_code == 200
            assert client.head(path).status_code == 200
        for path in ('/api', '/api/v1/absent', '/api/v2/absent', '/assets/absent',
                     '/assets/absent.js', '/.env', '/data/private/demo.sqlite3'):
            response = client.get(path)
            assert response.status_code == 404, path
            assert response.json()['error']['code'] == 'RESOURCE_NOT_FOUND'
        cases = {r['case_id']: r for r in map(json.loads, (ROOT / 'data/fixtures/cases.jsonl').read_text().splitlines())}
        for name in ('mixed', 'supported', 'nei', 'failed'):
            case = cases[name]
            response = client.post('/api/v1/checks', json=dict(
                schema_version='1.0', input_mode='text', confirmed_text=case['confirmed_text'],
                asset_id=None, asset_token=None, as_of='2026-11-08T17:00:00+07:00', consent_to_process=True))
            assert response.status_code == 202
            created = response.json()
            url = '/api/v1/checks/' + created['check']['check_id']
            headers = {'X-Resource-Token': created['access_token']}
            try:
                for _ in range(100):
                    response = client.get(url, headers=headers)
                    assert response.status_code == 200
                    record = response.json()
                    if record['status'] in ('completed', 'failed'):
                        break
                    time.sleep(.1)
                assert record['status'] == ('failed' if case['error'] else 'completed')
                if case['error']:
                    assert record['result'] is None and record['error']['code'] == case['error']
                    labels = {}
                else:
                    result = record['result']
                    assert result['run_mode'] == 'fixture' and result['usage']['attempts'] == 0
                    labels = dict(Counter(c['label'] for c in result['claims']))
                    assert labels == dict(Counter(c['label'] for c in case['result']['claims']))
                    for claim in result['claims']:
                        for evidence in claim['evidence']:
                            source = client.get('/api/v1/sources/' + evidence['version_id'])
                            assert source.status_code == 200
                            source = source.json()
                            assert source['is_fixture']
                            chunk = next(c for c in source['chunks'] if c['chunk_id'] == evidence['chunk_id'])
                            span = evidence['quote_span']
                            assert chunk['text'][span['start']:span['end']] == evidence['quote']
                assert client.get(url).status_code == 404
                results.append({'case': name, 'status': record['status'], 'labels': labels})
            finally:
                assert client.delete(url, headers=headers).status_code == 204
                assert client.get(url, headers=headers).status_code == 404
    return {'schema_version': '1.0', 'mode': 'fixture', 'provider_calls': 0,
            'static_api_source_delete': 'passed', 'cases': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    print(json.dumps(smoke(args.base_url), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
