import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8130', trace: 'retain-on-failure' },
  webServer: {
    command: '"C:\\Users\\shett\\AppData\\Local\\Python\\bin\\python.exe" e2e/start-test-server.py',
    url: 'http://127.0.0.1:8130/healthz',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
