"""Read-only Gemini readiness: load an owner secret without a shell, never generate content."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat

import httpx
from pydantic import SecretStr

DEFAULT_SECRET = Path.home()/'.config/tinchac/gemini.env'


def load_key(path: Path = DEFAULT_SECRET) -> SecretStr:
    """Read one literal assignment through a private regular-file descriptor. No expansion/eval."""
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 65536):
            raise ValueError
        with os.fdopen(fd, encoding='utf-8') as stream:
            fd = None
            lines = stream.read(65537).splitlines()
        values = []
        for line in lines:
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            match = re.fullmatch(r'\s*(?:export\s+)?GEMINI_API_KEY\s*=\s*(.*?)\s*',line)
            if match is None:
                # Owner env files may also carry configuration. Do not load,
                # expand or execute those values; only extract the Gemini key.
                if re.fullmatch(r'\s*(?:export\s+)?[A-Za-z_][A-Za-z_0-9]*\s*=.*',line):
                    continue
                raise ValueError
            value = match[1]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if not value or len(value) > 8192 or re.search(r'[\s$`\\\x00-\x1f\x7f]',value):
                raise ValueError
            values.append(value)
        if len(values) != 1:
            raise ValueError
        return SecretStr(values[0])
    except (OSError, ValueError, UnicodeError):
        raise ValueError('Secret unavailable: require an owner-only regular file with one literal GEMINI_API_KEY assignment.') from None
    finally:
        if fd is not None:
            os.close(fd)


def model_metadata(key: SecretStr, model: str, client) -> dict:
    if not re.fullmatch(r'gemini-[a-z0-9][a-z0-9.-]{0,100}', model):
        raise ValueError('Invalid model identifier')
    # No query-string key, redirects, generation/count-token call or raw error response.
    try:
        response = client.get('https://generativelanguage.googleapis.com/v1beta/models/'+model,
            headers={'x-goog-api-key':key.get_secret_value()},follow_redirects=False)
        result = {'request_type':'model_metadata_GET','requests':1,'http_status':response.status_code,
                  'accessible':False,'generate_content_advertised':False}
        if response.status_code != 200 or len(response.content) > 65536:
            return result
        data = response.json()
        if data.get('name') != 'models/'+model:
            return result
        result.update(accessible=True,generate_content_advertised='generateContent' in data.get('supportedGenerationMethods',[]))
        for source,target in [('inputTokenLimit','input_token_limit'),('outputTokenLimit','output_token_limit')]:
            value = data.get(source)
            result[target] = value if type(value) is int and value > 0 else None
        return result
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return {'request_type':'model_metadata_GET','requests':1,'http_status':None,
                'accessible':False,'generate_content_advertised':False,'error':'metadata_unavailable'}


def readiness(secret_file, model, *, client):
    result = {'checked_at':datetime.now(timezone.utc).isoformat(),'model':model,
        'key_loaded':False,'billing_verified':False,'quota_verified':False,'inference_verified':False,
        'generation_attempts':0,'generation_cost_usd':0,
        'preflight_status':'blocked','blockers':[],
        'authorization':{'max_generation_attempts':3,'max_cost_usd':0.03},
        'note':'Read-only model metadata is not an inference, quota, plan, price or billing verification.'}
    try:
        key = load_key(secret_file)
    except ValueError:
        result['blockers'].append('secret_missing_or_invalid')
        return result
    result['key_loaded'] = True
    result['metadata'] = model_metadata(key,model,client)
    if not result['metadata']['accessible'] or not result['metadata']['generate_content_advertised']:
        result['blockers'].append('model_generation_access_unverified')
    # The available API key grants Gemini access, not a Cloud Billing OAuth session.
    # Do not turn key existence or models.get success into a fabricated billing receipt.
    result['blockers'] += ['no_authenticated_billing_verification','account_quota_and_plan_unverified']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--secret-file',type=Path,default=DEFAULT_SECRET)
    parser.add_argument('--model',default='gemini-3.5-flash-lite')
    parser.add_argument('--report',type=Path,required=True,help='New metadata-only JSON receipt, never overwritten')
    args = parser.parse_args()
    # Refuse an existing output before any API request.
    with args.report.open('x') as output:
        with httpx.Client(timeout=15,trust_env=False) as client:
            result=readiness(args.secret_file,args.model,client=client)
        json.dump(result,output,ensure_ascii=False,indent=2)
        output.write('\n')
    print(json.dumps(result,ensure_ascii=False))
    return 2  # Never calls generation while billing is unverified.


if __name__=='__main__':
    raise SystemExit(main())
