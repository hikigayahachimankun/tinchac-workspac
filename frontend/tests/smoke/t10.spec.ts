import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const evidence=fileURLToPath(new URL('../../../docs/evidence/T10/',import.meta.url));
const fixture=JSON.parse(await readFile(new URL('../../src/api/fixture-texts.json',import.meta.url),'utf8')) as Record<string,string>;
const completed=JSON.parse(await readFile(new URL('../../../contracts/examples/check_result.json',import.meta.url),'utf8'));
const created=JSON.parse(await readFile(new URL('../../../contracts/examples/CheckCreated.json',import.meta.url),'utf8'));
const source=JSON.parse(await readFile(new URL('../../../contracts/examples/SourcePublic.json',import.meta.url),'utf8'));
const failure={schema_version:'1.0',request_id:'test',error:{code:'INTERNAL_ERROR',message:'Test transport failure',retryable:true,details:{}}};
async function start(page:import('@playwright/test').Page) {
 await page.goto('/');await page.getByLabel('Nội dung thông báo').fill(fixture.mixed!);
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();
}
for(const width of [390,1440]) {
 test(`T10 HTTP fixture text, keyboard, source loss and image confirmation ${width}`,async({page})=>{
  await mkdir(evidence,{recursive:true});await page.setViewportSize({width,height:900});
  let posts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/checks')) posts++;});
  await page.goto('/');await page.screenshot({path:`${evidence}/input-${width}.png`,fullPage:true});
  await page.getByLabel('Nội dung thông báo').fill(fixture.mixed!);
  await page.getByLabel('Nội dung thông báo').focus();await page.keyboard.press('Tab');await page.keyboard.press('Tab');
  await expect(page.getByRole('checkbox')).toBeFocused();await page.keyboard.press('Space');await page.keyboard.press('Tab');await page.keyboard.press('Enter');
  await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible();await expect(page.locator('.output')).toBeFocused();
  await expect(page.locator('.verdict')).toHaveText(['Được nguồn hỗ trợ','Mâu thuẫn với nguồn','Chưa đủ bằng chứng']);
  const summary=page.locator('.evidence summary').first();await summary.focus();await page.keyboard.press('Enter');
  await expect(page.getByText('Lưu snapshot',{exact:true})).toBeVisible();
  await page.route('https://tinchac.example/**',route=>route.abort()); // The original site may be absent; snapshot is independent.
  await page.locator('.snapshot summary').first().click();await expect(page.locator('.snapshot p').first()).toContainText('Học bổng');
  await expect(page.locator('.evidence a')).toHaveCount(0); // Fixture identifier never navigates.
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:`${evidence}/evidence-${width}.png`,fullPage:true});
  await page.getByRole('button',{name:'Ảnh',exact:true}).click();
  await page.locator('#image-file').setInputFiles(fileURLToPath(new URL('../../../data/fixtures/ocr/vietnamese-clear.png',import.meta.url)));
  await expect(page.locator('#ocr-text')).toHaveValue(/7 triệu/);expect(posts).toBe(1);
  await page.locator('#ocr-text').fill(fixture.supported!);await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).focus();await page.keyboard.press('Enter');
  await expect(page.locator('.summary-counts')).toContainText('1 được nguồn hỗ trợ');expect(posts).toBe(2);
  await expect(page.locator('.verdict')).toHaveCount(1);
  await page.screenshot({path:`${evidence}/image-result-${width}.png`,fullPage:true});
 });
}
test('T10 all-N, failed, expired and backend steps are distinct',async({page})=>{
 await start(page);await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible();
 await page.getByText('Tình huống mô phỏng',{exact:true}).click();await page.getByLabel('Chọn kết quả mẫu').selectOption('nei');
 await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();await expect(page.locator('.verdict')).toHaveText(['Chưa đủ bằng chứng']);
 await expect(page.getByRole('heading',{name:'Phạm vi nguồn đã đối chiếu'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Bước kiểm tra tiếp theo'})).toBeVisible();
 await page.screenshot({path:`${evidence}/all-N.png`,fullPage:true});
 await page.getByLabel('Chọn kết quả mẫu').selectOption('failed');await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();
 await expect(page.getByRole('alert')).toContainText('PROVIDER_TIMEOUT');await expect(page.locator('.verdict')).toHaveCount(0);
 await page.screenshot({path:`${evidence}/failed.png`,fullPage:true});
});
test('T10 GET failure retries same job; long loading stops and cancel deletes without POST',async({page})=>{
 let posts=0;let failGet=true;let deletes=0;
 await page.route('**/api/v1/checks',async route=>{posts++;await route.continue();});
 await page.route('**/api/v1/checks/*',async route=>{
  if(route.request().method()==='DELETE'){deletes++;await route.continue();return;}
  if(failGet){failGet=false;await route.fulfill({status:503,json:failure});return;}
  const response=await route.fetch();const body=await response.json();await route.fulfill({json:{...body,status:'retrieving',error:null,result:null}});
 });
 await page.clock.install();await start(page);await page.clock.fastForward(1600);
 await expect(page.getByRole('alert')).toContainText('Test transport failure');expect(posts).toBe(1);
 await page.getByRole('button',{name:'Kiểm tra lại trạng thái'}).click();await page.clock.fastForward(121000);
 await expect(page.getByRole('heading',{name:'Đang xử lý lâu'})).toBeVisible();expect(posts).toBe(1);
 await page.screenshot({path:`${evidence}/slow.png`,fullPage:true});
 await page.getByRole('button',{name:'Hủy và xóa phiên kiểm tra'}).click();await expect(page.getByRole('status')).toContainText('Đã hủy');
 expect(deletes).toBe(1);expect(posts).toBe(1);await expect(page.locator('.verdict')).toHaveCount(0);
});
for(const mode of ['live','replay'] as const) {
 test(`T10 ${mode} metadata, warnings, expired and safe public snapshot links`,async({page})=>{
  await page.route('**/api/v1/health',route=>route.fulfill({json:{schema_version:'1.0',run_mode:mode}}));
  await page.route('**/api/v1/checks',route=>route.fulfill({status:202,json:created}));
  const steps=['Bước backend giữ nguyên. https://unapproved.example/pay','<img src=x onerror=alert(1)>'];
  const result={...completed.result,run_mode:mode,next_steps:steps,warnings:['Cảnh báo hệ thống <b>không phải kết luận</b>'],sources:[{...source,is_fixture:false}],claims:completed.result.claims.map((c:object)=>({...c,temporal_status:'expired'}))};
  await page.route('**/api/v1/checks/*',route=>route.request().method()==='DELETE'?route.fulfill({status:204}):route.fulfill({json:{...completed,result}}));
  let snapshots=0;
  await page.route('**/api/v1/sources/*',route=>{snapshots++;return snapshots===1?route.fulfill({status:503,json:failure}):route.fulfill({json:{...source,is_fixture:false,canonical_url:'https://dut.udn.vn/notice',text:'<script>not HTML</script>'}});});
  await page.goto('/');await expect(page.locator('.fixture-banner')).toContainText(mode==='live'?'Live':'Replay');
  await page.getByLabel('Nội dung thông báo').fill(fixture.mixed!);await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Kiểm tra thông báo',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible();await expect(page.locator('.results')).toContainText('hết hạn không chứng minh giả mạo');
  await expect(page.locator('.next-steps a')).toHaveCount(0);await expect(page.locator('.next-steps')).toContainText(steps[1]!);
  await page.locator('.evidence summary').first().click();await expect(page.getByRole('button',{name:'Thử tải lại snapshot'})).toBeVisible();
  await expect(page.locator('blockquote').first()).toHaveText(completed.result.claims[0].evidence[0].quote);
  await page.getByRole('button',{name:'Thử tải lại snapshot'}).click();await page.locator('.snapshot summary').click();
  await expect(page.locator('.snapshot p')).toHaveText('<script>not HTML</script>');
  const link=page.getByRole('link',{name:'Mở trang nguồn gốc (tab mới)'});await expect(link).toHaveAttribute('rel','noopener noreferrer');await expect(link).toHaveAttribute('target','_blank');
  await page.screenshot({path:`${evidence}/${mode}.png`,fullPage:true});
 });
}
test('T10 cancel during POST deletes late resource and never displays late result',async({page})=>{
 let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});let posted=false;let deleted=0;
 await page.route('**/api/v1/checks',async route=>{posted=true;const response=await route.fetch();await gate;await route.fulfill({response});});
 page.on('request',r=>{if(r.method()==='DELETE'&&r.url().includes('/checks/')) deleted++;});
 await start(page);await expect.poll(()=>posted).toBe(true);
 await page.getByRole('button',{name:'Hủy và xóa phiên kiểm tra'}).click();release();
 await expect.poll(()=>deleted).toBe(1);await expect(page.getByRole('button',{name:'Kiểm tra mô phỏng'})).toBeEnabled();
 await expect(page.locator('.verdict')).toHaveCount(0);
});
test('T10 unavailable health blocks POST; transport failure never automatically resubmits',async({page})=>{
 let healthy=false;let posts=0;
 await page.route('**/api/v1/health',route=>healthy?route.continue():route.fulfill({status:503,json:failure}));
 await page.route('**/api/v1/checks',route=>{posts++;return route.abort('connectionrefused');});
 await page.goto('/');await expect(page.getByRole('button',{name:'Thử đọc lại chế độ'})).toBeVisible();
 await expect(page.locator('button[type=submit]')).toBeDisabled();expect(posts).toBe(0);
 healthy=true;await page.getByRole('button',{name:'Thử đọc lại chế độ'}).click();
 await page.getByLabel('Nội dung thông báo').fill(fixture.mixed!);await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();
 await expect(page.getByRole('alert')).toContainText('Không kết nối được FastAPI');
 await expect(page.getByRole('alert')).toContainText('Lần trước có thể đã phát sinh chi phí');
 await expect(page.getByRole('button',{name:'Thử lại mô phỏng'})).toBeVisible();
 await page.waitForTimeout(1700);expect(posts).toBe(1);await expect(page.locator('.verdict')).toHaveCount(0);
});
test('T10 cancel OCR stops stale GET from replacing manual text and deletes asset',async({page})=>{
 let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});let polling=false;let deletes=0;
 await page.route('**/api/v1/assets/*',async route=>{
  if(route.request().method()==='DELETE'){deletes++;await route.continue();return;}
  const response=await route.fetch();polling=true;await gate;await route.fulfill({response});
 });
 await page.goto('/');await page.getByRole('button',{name:'Ảnh',exact:true}).click();
 await page.locator('#image-file').setInputFiles(fileURLToPath(new URL('../../../data/fixtures/ocr/vietnamese-clear.png',import.meta.url)));
 await expect.poll(()=>polling).toBe(true);await page.getByRole('button',{name:'Dừng OCR và nhập tay'}).click();
 await page.locator('#ocr-text').fill(fixture.supported!);release();
 await expect.poll(()=>deletes).toBe(1);await expect(page.locator('#ocr-text')).toHaveValue(fixture.supported!);
 const submitted=page.waitForRequest(r=>r.method()==='POST'&&r.url().endsWith('/checks'));
 await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Xác nhận chữ và kiểm tra'}).click();
 expect((await submitted).postDataJSON()).toMatchObject({input_mode:'text',asset_id:null,asset_token:null,confirmed_text:fixture.supported});
 await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible();
});
