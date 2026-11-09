import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'./tests/smoke',workers:1,timeout:45000,
 use:{baseURL:'http://127.0.0.1:5174',headless:true,launchOptions:{executablePath:process.env.TINCHAC_CHROMIUM_PATH}},
 webServer:[
  {command:'../.venv/bin/python -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8000',env:{DATABASE_PATH:'/tmp/tinchac-t04-smoke.sqlite3',APP_MODE:'fixture'},url:'http://127.0.0.1:8000/api/v1/health',reuseExistingServer:false},
  {command:'npm run dev -- --port 5174 --strictPort',env:{VITE_API_MODE:'http'},url:'http://127.0.0.1:5174',reuseExistingServer:false},
 ],
});
