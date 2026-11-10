import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/smoke', testMatch: 'fixture.spec.ts', workers: 1, timeout: 45000,
  use: {baseURL: 'http://127.0.0.1:8016', headless: true,
    launchOptions: {executablePath: process.env.TINCHAC_CHROMIUM_PATH}},
  webServer: {
    command: '../.venv/bin/python -m scripts.init_db && ../.venv/bin/python -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8016',
    env: {PYTHONPATH: '..', APP_MODE: 'fixture', FRONTEND_DIST: 'dist',
      DATABASE_PATH: '/tmp/tinchac-release-smoke.sqlite3', PRIVATE_DIR: '/tmp/tinchac-release-smoke-private'},
    url: 'http://127.0.0.1:8016/api/v1/health', reuseExistingServer: false,
  },
});
