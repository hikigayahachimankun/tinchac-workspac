import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const fixture = JSON.parse(readFileSync(new URL('../../src/api/fixture-texts.json', import.meta.url), 'utf8'));
const created = JSON.parse(readFileSync(new URL('../../../contracts/examples/CheckCreated.json', import.meta.url), 'utf8'));
const completed = JSON.parse(readFileSync(new URL('../../../contracts/examples/check_result.json', import.meta.url), 'utf8'));
const evidence = process.env.TINCHAC_EVIDENCE_ROOT ? process.env.TINCHAC_EVIDENCE_ROOT+'/T12/' : fileURLToPath(new URL('../../../docs/evidence/T12/', import.meta.url));
const sample = fileURLToPath(new URL('../../../data/fixtures/ocr/blank.png', import.meta.url));

for (const width of [390, 1440]) {
  test(`T12 empty OCR manual confirmation and browser privacy ${width}`, async ({ page }) => {
    await mkdir(evidence, { recursive: true });
    await page.setViewportSize({ width, height: 900 });
    const urls: string[] = [], tokens: string[] = [], logs: string[] = [], crashes: string[] = [];
    let posts = 0;
    page.on('request', request => {
      urls.push(request.url());
      if (request.method() === 'POST' && request.url().endsWith('/checks')) posts++;
    });
    page.on('response', async response => {
      if (response.request().method() === 'POST' && /\/(assets|checks)$/.test(response.url()) && response.status() === 202) {
        const body = await response.json(); tokens.push(body.access_token);
      }
    });
    page.on('console', message => logs.push(message.text()));
    page.on('pageerror', error => crashes.push(error.message));
    await page.goto('/');
    await page.getByRole('button', { name: 'Ảnh', exact: true }).click();
    await page.getByLabel('Chọn ảnh thông báo').setInputFiles(sample);
    await expect(page.getByRole('status')).toContainText('Không đọc được chữ', { timeout: 15000 });
    await expect(page.locator('#ocr-text')).toHaveValue('');
    expect(posts).toBe(0);
    await page.locator('#ocr-text').fill(fixture.mixed);
    await page.getByRole('button', { name: 'Xác nhận chữ và kiểm tra' }).click();
    await expect(page.getByRole('alert')).toContainText('Hãy xác nhận');
    expect(posts).toBe(0);
    await page.getByRole('checkbox').focus(); await page.keyboard.press('Space');
    await page.keyboard.press('Tab'); await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { name: 'Phiếu đối chiếu' })).toBeVisible();
    await expect(page.locator('.verdict')).toHaveText(['Được nguồn hỗ trợ', 'Mâu thuẫn với nguồn', 'Chưa đủ bằng chứng']);
    expect(posts).toBe(1);
    const storage = await page.evaluate(() => ({ local: { ...localStorage }, session: { ...sessionStorage }, cookie: document.cookie }));
    expect(storage).toEqual({ local: {}, session: {}, cookie: '' });
    expect(tokens.length).toBe(2);
    for (const token of tokens) {
      expect(urls.every(url => !url.includes(token))).toBe(true);
      expect(logs.every(log => !log.includes(token))).toBe(true);
    }
    expect(urls.every(url => !decodeURIComponent(url).includes(fixture.mixed))).toBe(true);
    expect(logs.every(log => !log.includes(fixture.mixed))).toBe(true);
    expect(crashes).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([]);
    await page.screenshot({ path: `${evidence}/empty-ocr-confirmed-${width}.png`, fullPage: true });
    await page.getByRole('button', { name: 'Hủy và xóa phiên kiểm tra' }).click();
    await expect(page.locator('.verdict')).toHaveCount(0);
    await page.getByRole('button', { name: 'Văn bản', exact: true }).click();
    // No raw URL, body, token, browser console or user data is written to the artifact.
    await writeFile(`${evidence}/privacy-${width}.json`, JSON.stringify({
      width, run_mode: 'fixture', checks_posted: posts, tokens_in_urls: false,
      private_content_in_console: false, storage_empty: true, browser_crashes: crashes.length,
      screenshot: 'synthetic fixture only',
    }, null, 2) + '\n');
  });
}

test('T12-B01 malformed successful API response must show a technical error instead of crashing', async ({ page }) => {
  const crashes: string[] = []; page.on('pageerror', error => crashes.push(error.message));
  await page.route('**/api/v1/checks', route => route.fulfill({ status: 202, json: created }));
  await page.route('**/api/v1/checks/*', route => route.request().method() === 'DELETE'
    ? route.fulfill({ status: 204 })
    : route.fulfill({ json: { ...completed, result: { ...completed.result, summary: null } } }));
  await page.goto('/');
  await page.getByLabel('Nội dung thông báo').fill(fixture.mixed);
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Kiểm tra mô phỏng' }).click();
  await expect(page.getByRole('alert')).toContainText('Lỗi kỹ thuật', { timeout: 5000 });
  await expect(page.locator('.verdict')).toHaveCount(0);
  expect(crashes).toEqual([]);
});
