import { defineConfig } from '@playwright/test'
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL
export default defineConfig({
  testDir: './tests', timeout: 45000, workers: 1,
  use: { baseURL: externalBaseUrl || 'http://127.0.0.1:5176', headless: true,
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
  webServer: externalBaseUrl ? undefined : { command: 'npm run dev -- --host 127.0.0.1 --port 5176', url: 'http://127.0.0.1:5176', reuseExistingServer: !process.env.CI },
})
