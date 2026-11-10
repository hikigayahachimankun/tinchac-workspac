# T12 — command receipts

Các blocks audit dưới đây được chạy trong phiên. Canary là tổng hợp, không phải dữ liệu cá nhân. Các lệnh test/build chính ở reports/qa_smoke.md. /tmp có thể bị hệ thống dọn.

## Browser wrapper thực chạy

Lưu block Python này tại /tmp/tinchac-t12-browser.py, chạy từ repo root:

```python
import os, subprocess, tempfile, shutil, sys
from pathlib import Path
root=Path.cwd()
backup=Path(tempfile.mkdtemp(prefix='tinchac-T12-evidence-'))
originals=[p for p in (root/'docs/evidence').iterdir() if p.is_dir() and p.name!='T12']
for path in originals:
    shutil.copytree(path, backup/path.name)
env=os.environ.copy()
env.update(TINCHAC_CHROMIUM_PATH='/tmp/tinchac-chrome/chrome-linux64/chrome', LD_LIBRARY_PATH='/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu')
args=['npm','run',sys.argv[1],'--prefix','frontend']
if len(sys.argv)>2: args += ['--'] + sys.argv[2:]
try:
    result=subprocess.run(args,env=env)
    print(f'T12_BROWSER_EXIT={result.returncode}',flush=True)
finally:
    for path in originals:
        shutil.rmtree(path)
        shutil.copytree(backup/path.name,path)
    shutil.rmtree(backup)
sys.exit(result.returncode)
```

```bash
python3 /tmp/tinchac-t12-browser.py test:fixture t12.spec.ts
python3 /tmp/tinchac-t12-browser.py test:fixture
python3 /tmp/tinchac-t12-browser.py test:browser
```

Focused T12 đầu chạy trước sửa B01. Full fixture có nhiều lượt; chỉ lượt cuối 20/20 trên mã cố định là acceptance. Wrapper restore evidence cả khi tests fail. Không audit SHA giữa lúc wrapper còn chạy.

## OCR command thực chạy (không sinh/sửa ảnh)

```bash
.venv/bin/python - <<'PY'
import json,unicodedata
from pathlib import Path
from backend.app.services.ocr import extract_image
from scripts.ocr_smoke import distance
root=Path.cwd()
reference=' '.join(unicodedata.normalize('NFC',(root/'data/fixtures/ocr/reference.txt').read_text()).split())
rows=[]
for sample in ('vietnamese-clear','vietnamese-blurred'):
    result=extract_image(root/f'data/fixtures/ocr/{sample}.png')
    actual=' '.join(unicodedata.normalize('NFC',result.text).split())
    edits=distance(actual,reference)
    rows.append(dict(sample=sample,split='synthetic dev fixture; one family; not test/gold',reference_chars=len(reference),character_edits=edits,cer=edits/len(reference),money_exact=('7 triệu' in actual),date_exact=None,url_exact=None,mean_confidence=result.mean_confidence,duration_ms=result.duration_ms))
report=dict(required_images=20,available_reference_images=2,available_families=1,split_test_available=False,
 normalization='NFC + collapsed whitespace; punctuation/case/accents preserved',automatic=rows,
 corrected=dict(status='NOT RUN',reason='No consented human correction session; no correction times. Exact reference is not a measured user correction.'),
 limits='No heldout set. Date/URL absent in reference, therefore N/A. No changes to images/splits/gold.')
(root/'docs/evidence/T12/ocr-existing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
PY
```

## Uvicorn access-log command thực chạy

```bash
.venv/bin/python - <<'PY'
import json,os,subprocess,tempfile,time
from pathlib import Path
import httpx
from backend.app.db import initialize
canary='SYNTHETIC_T12_PRIVATE_LOG_CANARY'
root=Path.cwd()
with tempfile.TemporaryDirectory(prefix='tinchac-t12-access-') as folder:
    work=Path(folder); database=work/'qa.sqlite3'; initialize(database)
    env=os.environ | {'APP_MODE':'fixture','DATABASE_PATH':str(database),'PRIVATE_DIR':str(work/'private'),'GEMINI_API_KEY':''}
    with (work/'server.log').open('w+') as log:
        server=subprocess.Popen([str(root/'.venv/bin/python'),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8012'],env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            with httpx.Client(base_url='http://127.0.0.1:8012',timeout=5) as client:
                for _ in range(100):
                    try:
                        if client.get('/api/v1/health').status_code==200: break
                    except httpx.TransportError: pass
                    time.sleep(.05)
                else: raise RuntimeError('Local QA server not ready')
                payload=json.loads((root/'contracts/examples/check_create.json').read_text()) | {'confirmed_text':canary}
                accepted=client.post('/api/v1/checks',json=payload)
                assert accepted.status_code==202
                created=accepted.json(); token=created['access_token']; url='/api/v1/checks/'+created['check']['check_id']
                record=client.get(url,headers={'X-Resource-Token':token}).json()
                assert record['status']=='failed' and record['result'] is None
                invalid=client.post('/api/v1/checks',json=payload|{'consent_to_process':False,'private_field':canary})
                assert invalid.status_code==422 and canary not in invalid.text
                invalid_image=client.post('/api/v1/assets',files={'file':(canary+'.png',b'not an image','image/png')})
                assert invalid_image.status_code==415 and canary not in invalid_image.text
                assert client.delete(url,headers={'X-Resource-Token':token}).status_code==204
        finally:
            server.terminate(); server.wait(timeout=5)
        log.seek(0); output=log.read()
        assert canary not in output and token not in output
        report={'mode':'fixture','server':'uvicorn localhost:8012','request_text_in_access_logs':False,'capability_in_access_logs':False,
                'filename_in_access_logs':False,'validation_echo':False,'invalid_upload_echo':False,
                'statuses':{'create':202,'validation':422,'upload':415,'delete':204},
                'note':'Synthetic canary; raw log and temporary DB deleted after scan. Header/body requests only, not query-string misuse.'}
        (root/'docs/evidence/T12/access-log-audit.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
PY
```

## Ignore/bundle và build fingerprint

Đã chạy git check-ignore --no-index --stdin từ Python subprocess với 10 đường dẫn liệt kê nguyên văn trong privacy-audit.json; tất cả ignored. Pattern scan dùng Python re.compile(rb'AIza[0-9A-Za-z_-]{35}') trên frontend/dist/**/*.js và selected tracked source, chỉ báo counts; không đọc key thật để so sánh. Scan lại bundle sau build client cuối.

Build ID = t12- + 16 ký tự đầu SHA256 của canonical JSON mapping {path: sha256(file_bytes)}, sort_keys=True, separators=(',', ':'). Exact inventory tại build.json; snapshot ban đầu /tmp/tinchac-t12-upstream-hashes.json. client-only.patch được dựng và kiểm bằng inverse patch có SHA256 trùng snapshot upstream, giúp owner review phần T12 giữa thay đổi T10 chưa commit.
