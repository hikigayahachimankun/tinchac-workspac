// T15 browser rehearsal and real screen recording. Never opens external sites.
import { chromium } from '../frontend/node_modules/playwright-core/index.mjs';
import { expect } from '../frontend/node_modules/@playwright/test/index.mjs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const args = process.argv.slice(2);
function option(name, fallback) { const i = args.indexOf(name); return i < 0 ? fallback : args[i + 1]; }
const base = option('--base-url', 'http://127.0.0.1:8000');
const output = path.resolve(option('--output', '/tmp/tinchac-t15-browser'));
const record = args.includes('--record');
if (!['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw Error('Local demo only');
await mkdir(output); // Refuse to overwrite a recording/evidence directory.
const fixture = JSON.parse(await readFile(path.join(root, 'frontend/src/api/fixture-texts.json'), 'utf8'));
const browser = await chromium.launch({headless:true, executablePath:process.env.TINCHAC_CHROMIUM_PATH});
const results = [];
try {
 for (const width of record ? [1280] : [390, 1440]) {
  const context = await browser.newContext({viewport:{width,height:900},
    ...(record ? {recordVideo:{dir:output,size:{width,height:900}}} : {})});
  const page = await context.newPage();
  const errors = [], external = [], traffic = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', response => {
    const url = new URL(response.url());
    if (url.pathname.startsWith('/api/')) traffic.push(`${response.request().method()} ${url.pathname} ${response.status()}`);
  });
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== new URL(base).origin && !['blob:', 'data:'].includes(url.protocol)) {
      external.push(url.origin); await route.abort();
    } else await route.continue();
  });
  await page.goto(base);
  await expect(page.getByText('Chế độ mô phỏng',{exact:true})).toBeVisible();
  const started = Date.now();
  async function caption(title, text) {
    if (record) await page.evaluate(({title,text}) => {
      let box = document.getElementById('recording-caption');
      if (!box) {
        box = document.createElement('aside'); box.id = 'recording-caption';
        box.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:9999;padding:16px 32px;background:#122b2a;color:white;font:20px/1.5 system-ui;border-top:4px solid #e4ae53;pointer-events:none';
        document.body.append(box); document.body.style.paddingBottom = '140px';
      }
      box.replaceChildren(); const strong = document.createElement('strong'); strong.textContent = 'FIXTURE · ' + title;
      const line = document.createElement('div'); line.textContent = text; box.append(strong,line);
    }, {title,text});
  }
  async function hold(until) {
    if (record) await page.waitForTimeout(Math.max(0, until * 1000 - (Date.now() - started)));
  }
  async function shot(name) {
    await page.screenshot({path:path.join(output,`${name}-${width}.png`),fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  async function textCase(name, labels) {
    await page.getByRole('button',{name:'Văn bản',exact:true}).click();
    await page.getByLabel('Nội dung thông báo').fill(fixture[name]);
    await page.getByRole('checkbox').check();
    await page.getByRole('button',{name:'Kiểm tra mô phỏng',exact:true}).click();
    if (labels) {
      await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible();
      await expect(page.locator('.verdict')).toHaveText(labels);
    }
  }
  await caption('TinChắc · Bản ứng viên nội bộ · FIXTURE',
    'Đối chiếu từng chi tiết học bổng / thu phí. Toàn bộ thao tác sau dùng dữ liệu tự tạo; không gọi Gemini.');
  await shot('input'); await hold(25);

  await caption('01 · Ảnh → OCR cục bộ → xác nhận chữ',
    'Ảnh tổng hợp: 7 triệu. Nguồn mô phỏng: 5 triệu. Kiểm tra số tiền, ngày và sửa chữ trước khi gửi.');
  await page.getByRole('button',{name:'Ảnh',exact:true}).click();
  await page.getByLabel('Chọn ảnh thông báo').setInputFiles(path.join(root,'data/fixtures/ocr/vietnamese-clear.png'));
  const ocr = page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)');
  await expect(ocr).toBeEnabled();
  await expect(page.getByText('Đang đọc chữ từ ảnh…',{exact:true})).toHaveCount(0,{timeout:30000});
  expect(await ocr.inputValue()).toContain('7');
  await ocr.fill(fixture.original);
  await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
  await expect(page.locator('.verdict')).toHaveText(['Mâu thuẫn với nguồn']);
  await page.locator('.evidence summary').first().click();
  await expect(page.getByText('Lưu snapshot',{exact:true})).toBeVisible();
  await page.locator('.snapshot summary').click();
  await expect(page.locator('.snapshot p')).toContainText('5.000.000');
  await shot('ocr-contradicted'); await hold(50);
  await ocr.fill(fixture.supported);
  await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
  await expect(page.locator('.verdict')).toHaveText(['Được nguồn hỗ trợ']);
  await caption('02 · Có trường hợp được nguồn hỗ trợ',
    'Sửa chữ thành 5 triệu: kết quả được hỗ trợ trong fixture. Đây chưa phải nghiệm thu một thông báo DUT thật.');
  await page.locator('.output').scrollIntoViewIfNeeded(); await shot('supported'); await hold(85);

  await caption('03 · Khoản phí chưa đủ bằng chứng',
    'Nguồn im lặng về phí giữ suất 300.000 đồng. Không suy ra mâu thuẫn hoặc lừa đảo; hỏi kênh chính thức.');
  await textCase('nei',['Chưa đủ bằng chứng']);
  await page.locator('.output').scrollIntoViewIfNeeded(); await shot('nei'); await hold(115);

  await caption('Ba nhãn · Nguồn và thời điểm',
    'Mở trích đoạn và snapshot đã lưu. Hết hạn là trạng thái riêng; hết hạn không chứng minh giả mạo.');
  await textCase('mixed',['Được nguồn hỗ trợ','Mâu thuẫn với nguồn','Chưa đủ bằng chứng']);
  await expect(page.locator('.output')).toBeFocused();
  const evidence = page.locator('.evidence summary').first();
  await evidence.focus(); await page.keyboard.press('Enter');
  await expect(page.getByText('Lưu snapshot',{exact:true})).toBeVisible();
  await page.locator('.snapshot summary').click();
  await expect(page.locator('.snapshot p')).toContainText('5.000.000');
  await shot('evidence'); await hold(145);

  await caption('04 · Lỗi kỹ thuật không phải kết luận',
    'Lỗi worker mô phỏng: không hiện nhãn. Luồng quota và cap cũng đã được kiểm bằng adapter/ledger thật với provider mock.');
  await textCase('failed');
  await expect(page.getByRole('alert')).toContainText('PROVIDER_TIMEOUT');
  await expect(page.locator('.verdict')).toHaveCount(0);
  await page.locator('.output').scrollIntoViewIfNeeded(); await shot('worker-error'); await hold(170);

  await caption('Diễn tập mất kết nối · fault injection',
    'Chặn POST trong trình duyệt: báo lỗi kết nối, không đổi sang NEI. Bản fixture local và video là dự phòng có nhãn.');
  await page.route('**/api/v1/checks',route=>route.abort('connectionrefused'));
  await textCase('supported');
  await expect(page.getByRole('alert')).toContainText('Không kết nối được FastAPI');
  await expect(page.locator('.verdict')).toHaveCount(0); await shot('offline'); await hold(190);
  await page.unroute('**/api/v1/checks');

  await caption('Diễn tập hết quota · phản hồi HTTP giả lập',
    'HTTP 429 được chèn tại trình duyệt; không tiêu hao quota thật. Dừng gọi, không tự chuyển dịch vụ trả phí.');
  await page.route('**/api/v1/checks',route=>route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({
    schema_version:'1.0',request_id:'00000000-0000-4000-8000-000000000001',
    error:{code:'RATE_LIMITED',message:'Quota fault injection; no provider request.',retryable:false,details:{}}})}));
  await textCase('supported');
  await expect(page.getByRole('alert')).toContainText('RATE_LIMITED');
  await expect(page.locator('.verdict')).toHaveCount(0); await shot('quota'); await hold(205);
  await page.unroute('**/api/v1/checks');
  await textCase('supported',['Được nguồn hỗ trợ']);
  await caption('Giới hạn trước bàn giao T16 / T17',
    'Cold start WSL + CI Ubuntu độc lập đạt; laptop demo vật lý chưa thử. Còn case DUT thật QA, benchmark/người thử/quyền phân phối; T15 chưa done.');
  await page.locator('.output').scrollIntoViewIfNeeded(); await shot('limits'); await hold(220);
  expect(await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage},cookie:document.cookie})))
    .toEqual({local:{},session:{},cookie:''});
  expect(errors).toEqual([]); expect(external).toEqual([]);
  const video = page.video();
  await context.close();
  results.push({width,mode:'fixture',cases:['OCR original→supported','nei','mixed','worker failure'],
    fault_injection:['connectionrefused','HTTP429'],external_requests:external.length,page_errors:errors,
    storage:'empty',video:video ? path.basename(await video.path()) : null});
  await writeFile(path.join(output,`network-${width}.log`),traffic.join('\n')+'\n');
 }
 await writeFile(path.join(output,'result.json'),JSON.stringify({record,provider_calls:0,results},null,2)+'\n');
 console.log(JSON.stringify({record,provider_calls:0,results},null,2));
} finally { await browser.close(); }
