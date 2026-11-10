import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const texts=JSON.parse(readFileSync(new URL('../../src/api/fixture-texts.json',import.meta.url),'utf8')) as Record<string,string>;
const samples=fileURLToPath(new URL('../../../data/fixtures/ocr/',import.meta.url));
const evidence=process.env.TINCHAC_EVIDENCE_ROOT ? process.env.TINCHAC_EVIDENCE_ROOT+'/T06/' : fileURLToPath(new URL('../../../docs/evidence/T06/',import.meta.url));

for(const width of [390,1440]) {
 test(`real OCR review edits money before explicit confirmation ${width}`,async({page})=>{
  await mkdir(evidence,{recursive:true});
  const checks:string[]=[];const network:string[]=[];
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.startsWith('/api/'))network.push(`${r.method()} ${path}`);if(path==='/api/v1/checks'&&r.method()==='POST')checks.push(r.postDataJSON().confirmed_text);});
  await page.setViewportSize({width,height:1000});await page.goto('/');
  await page.getByRole('button',{name:'Ảnh',exact:true}).click();
  await page.getByLabel('Chọn ảnh thông báo').setInputFiles(samples+'vietnamese-clear.png');
  const input=page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)');
  await expect(input).toHaveValue(texts.original!,{timeout:15000});
  expect(checks).toEqual([]);
  await expect(page.getByRole('img',{name:/Ảnh thông báo bạn đã chọn/})).toBeVisible();
  await page.screenshot({path:evidence+`ocr-clear-${width}.png`,fullPage:true});
  await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
  await expect(page.getByRole('alert')).toContainText('Hãy xác nhận');
  expect(checks).toEqual([]);
  await input.fill(texts.supported!);
  await input.focus();await page.keyboard.press('Tab');await page.keyboard.press('Space');
  await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'})).toBeFocused();
  const accepted=page.waitForResponse(r=>r.url().endsWith('/api/v1/checks')&&r.request().method()==='POST');
  await page.keyboard.press('Enter');
  const response=await accepted;expect(response.status()).toBe(202);
  const payload=response.request().postDataJSON();expect(payload.input_mode).toBe('image');expect(payload.confirmed_text).toBe(texts.supported);
  expect(payload.asset_id).toBeTruthy();expect(payload.asset_token).toBeTruthy();
  await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible({timeout:15000});
  const created=await response.json();
  const record=await page.request.get(`/api/v1/checks/${created.check.check_id}`,{headers:{'X-Resource-Token':created.access_token}});
  const result=(await record.json()).result;
  expect(result.summary.supported).toBe(1);expect(result.summary.contradicted).toBe(0);
  expect(result.claims[0].normalized.money.amount).toBe(5000000);
  expect(checks).toEqual([texts.supported]);
  expect(network.every(line=>!line.includes(payload.asset_token))).toBe(true);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:evidence+`ocr-edited-result-${width}.png`,fullPage:true});
  await writeFile(evidence+`network-${width}.txt`,network.join('\n')+'\nPOST confirmed_text: '+texts.supported+'\nResult: supported=1 contradicted=0 amount=5000000\n');
 });
}

test('blurred empty OCR keeps warning and accepts manual text after confirmation',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Ảnh',exact:true}).click();
 let posts=0;page.on('request',r=>{if(r.url().endsWith('/api/v1/checks')&&r.method()==='POST')posts++;});
 await page.getByLabel('Chọn ảnh thông báo').setInputFiles(samples+'vietnamese-blurred.png');
 await expect(page.getByRole('status')).toContainText('Không đọc được chữ',{timeout:15000});
 const input=page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)');
 await expect(input).toHaveValue('');expect(posts).toBe(0);
 await input.fill(texts.mixed!);await page.getByRole('checkbox').check();
 await page.screenshot({path:evidence+'ocr-blurred-manual.png',fullPage:true});
 await expect(page.getByRole('status')).toContainText('Không đọc được chữ');
 await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
 await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible({timeout:15000});
 expect(posts).toBe(1);
});

test('failed OCR keeps error and manual entry uses the text contract',async({page})=>{
 await page.route('**/api/v1/assets/*',async route=>{
  if(route.request().method()!=='GET')return route.continue();
  const response=await route.fetch();const asset=await response.json();
  await route.fulfill({response,json:{...asset,status:'failed',ocr:null,error:{code:'OCR_FAILED',message:'OCR lỗi mô phỏng; hãy nhập tay.',retryable:true,details:{}}}});
 });
 await page.goto('/');await page.getByRole('button',{name:'Ảnh',exact:true}).click();
 await page.getByLabel('Chọn ảnh thông báo').setInputFiles(samples+'blank.png');
 await expect(page.getByRole('status')).toContainText('OCR lỗi mô phỏng',{timeout:15000});
 await page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)').fill(texts.supported!);
 await page.getByRole('checkbox').check();
 await expect(page.getByRole('status')).toContainText('OCR lỗi mô phỏng');
 const post=page.waitForResponse(r=>r.url().endsWith('/api/v1/checks')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
 const payload=(await post).request().postDataJSON();
 expect(payload.input_mode).toBe('text');expect(payload.asset_id).toBeNull();expect(payload.asset_token).toBeNull();
 await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible({timeout:15000});
});

test('late OCR does not overwrite manual draft after polling stops',async({page})=>{
 await page.clock.install();
 let ready=false;let gets=0;
 await page.route('**/api/v1/assets/*',async route=>{
  if(route.request().method()!=='GET')return route.continue();
  const response=await route.fetch();const asset=await response.json();gets++;
  await route.fulfill({response,json:ready?asset:{...asset,status:'ocr',ocr:null,error:null}});
 });
 await page.goto('/');await page.getByRole('button',{name:'Ảnh',exact:true}).click();
 await page.getByLabel('Chọn ảnh thông báo').setInputFiles(samples+'vietnamese-clear.png');
 await expect.poll(()=>gets).toBeGreaterThan(0);
 await page.clock.fastForward(121000);
 await expect(page.getByRole('button',{name:'Kiểm tra lại OCR'})).toBeVisible();
 const input=page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)');
 await input.fill(texts.supported!);ready=true;
 await page.getByRole('button',{name:'Kiểm tra lại OCR'}).click();
 await page.clock.fastForward(1600);
 await expect(page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'})).toBeEnabled();
 await expect(input).toHaveValue(texts.supported!);
});

test('leaving a failed image check clears retry for the deleted asset',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Ảnh',exact:true}).click();
 await page.getByLabel('Chọn ảnh thông báo').setInputFiles(samples+'vietnamese-clear.png');
 await expect(page.getByLabel('Chữ để đối chiếu (có thể sửa hoặc nhập tay)')).toHaveValue(texts.original!,{timeout:15000});
 await page.route('**/api/v1/checks',route=>route.fulfill({status:503,json:{schema_version:'1.0',request_id:'fixture',error:{code:'INTERNAL_ERROR',message:'Fixture request failure',retryable:true,details:{}}}}));
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
 await expect(page.getByRole('button',{name:'Thử lại mô phỏng'})).toBeVisible();
 const deleted=page.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().includes('/assets/'));
 await page.getByRole('button',{name:'Văn bản',exact:true}).click();
 expect((await deleted).status()).toBe(204);
 await expect(page.getByRole('button',{name:'Thử lại mô phỏng'})).toHaveCount(0);
 await expect(page.getByRole('alert')).toHaveCount(0);
});
