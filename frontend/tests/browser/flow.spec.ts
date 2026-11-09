import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir } from 'node:fs/promises';
const screenshots='../.impeccable/review';
for(const width of [360,390,1440]) {
 test(`text, keyboard, mixed results and evidence at ${width}px`,async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:900});await page.goto('/');
  await mkdir(screenshots,{recursive:true});
  await expect(page.getByText('Chế độ mô phỏng',{exact:true})).toBeVisible();
  await page.screenshot({path:`${screenshots}/input-${width}.png`,fullPage:true});
  await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();
  await expect(page.getByLabel('Nội dung thông báo')).toBeFocused();
  await expect(page.getByRole('alert')).toContainText('20');
  await page.getByRole('button',{name:'Điền nội dung mẫu'}).click();
  await expect(page.getByLabel('Nội dung thông báo')).toBeFocused();
  await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'Điền nội dung mẫu'})).toBeFocused();
  await page.keyboard.press('Tab');await expect(page.getByRole('checkbox')).toBeFocused();
  await page.keyboard.press('Space');await page.keyboard.press('Tab');
  await expect(page.getByRole('button',{name:'Kiểm tra mô phỏng'})).toBeFocused();await page.keyboard.press('Enter');
  await expect(page.getByRole('heading',{name:'Đã tiếp nhận'})).toBeVisible();
  await page.screenshot({path:`${screenshots}/progress-${width}.png`,fullPage:true});
  await expect(page.getByRole('heading',{name:'Phiếu đối chiếu'})).toBeVisible({timeout:12000});
  await expect(page.locator('.output')).toBeFocused();
  await expect(page.locator('.verdict')).toHaveText(['Được nguồn hỗ trợ','Mâu thuẫn với nguồn','Chưa đủ bằng chứng']);
  const evidence=page.locator('.evidence summary').first();
  await evidence.focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('heading',{name:'Trích đoạn trong snapshot'})).toBeVisible();
  await expect(page.getByText('Lưu snapshot',{exact:true})).toBeVisible();
  await page.locator('.snapshot summary').first().click();
  await expect(page.locator('.snapshot p').first()).toHaveText('5.000.000 đồng/suất.');
  await page.keyboard.press('Tab'); // keyboard can leave details; no focus trap
  await expect(page.locator('body')).toBeVisible();
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:`${screenshots}/${width===1440?'desktop':width===390?'mobile':'user-360'}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(axe.violations).toEqual([]);expect(errors).toEqual([]);
  await evidence.focus();await page.keyboard.press('Enter');
  await expect(evidence).toBeFocused();await expect(page.locator('.evidence').first()).not.toHaveAttribute('open','');
 });
}
test('NEI and technical worker/request errors remain separate',async({page})=>{
 await page.setViewportSize({width:360,height:900});await page.goto('/');
 await page.getByRole('button',{name:'Điền nội dung mẫu'}).click();await page.getByRole('checkbox').check();
 await page.getByText('Tình huống mô phỏng',{exact:true}).click();
 for(const [scenario,title] of [['nei','Phiếu đối chiếu'],['failed','Chưa hoàn tất kiểm tra'],['request_error','Chưa hoàn tất kiểm tra'],['expired','Phiếu đối chiếu']]) {
  await page.getByLabel('Chọn kết quả mẫu').selectOption(scenario!);
  await page.getByRole('button',{name:'Kiểm tra mô phỏng'}).click();
  await expect(page.getByRole('heading',{name:title!,exact:true})).toBeVisible({timeout:12000});
  await expect(page.locator('.output')).toBeFocused();
  if(scenario==='nei') { await expect(page.locator('.technical-error')).toHaveCount(0);await expect(page.locator('.verdict')).toHaveText('Chưa đủ bằng chứng'); }
  else if(scenario==='expired') {await expect(page.locator('.verdict')).toHaveText('Được nguồn hỗ trợ');await expect(page.locator('.temporal')).toContainText('Đã hết hạn');}
  else { await expect(page.locator('.verdict')).toHaveCount(0);await expect(page.getByRole('alert')).toContainText('Lỗi kỹ thuật mô phỏng'); }
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:`${screenshots}/${scenario}-360.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 }
 await page.addStyleTag({content:'html{font-size:200%}'});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
