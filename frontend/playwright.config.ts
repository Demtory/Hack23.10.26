import fs from 'node:fs';
import path from 'node:path';
import { defineConfig } from '@playwright/test';

// Python для тестового сервера: PYTHON из окружения, затем venv проекта, затем системный.
const venvCandidates = [
  path.resolve(process.cwd(), '..', '.venv', 'bin', 'python'),
  path.resolve(process.cwd(), '..', '.venv', 'Scripts', 'python.exe'),
];
const venv = venvCandidates.find((candidate) => fs.existsSync(candidate));
const python = process.env.PYTHON ?? venv ?? (process.platform === 'win32' ? 'python' : 'python3');

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:8130', trace: 'retain-on-failure' },
  webServer: {
    command: `"${python}" e2e/start-test-server.py`,
    url: 'http://127.0.0.1:8130/healthz',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
