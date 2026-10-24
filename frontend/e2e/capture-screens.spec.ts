import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const outDir = path.resolve(__dirname, '..', '..', 'docs', 'screenshots');

test.beforeAll(() => {
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }
});

test('capture all screens and states', async ({ page }) => {
  // 1. Login screen
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/#/login');
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(outDir, '01-login.png'), fullPage: true });

  // 2. Dashboard / Overview
  await page.goto('/#/');
  await page.getByLabel('Пароль', { exact: true }).fill('admin123');
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Обзор риска' })).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '02-overview-1440.png'), fullPage: true });

  // 3. Customers list with filters (Urgency = 7d)
  await page.getByRole('link', { name: 'Клиенты', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Клиенты', exact: true })).toBeVisible();
  await page.getByLabel('Срочность').selectOption('7d');
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '03-customers-urgency-7d.png'), fullPage: true });

  // 4. Customer Card
  const firstLink = page.locator('table a').first();
  await firstLink.click();
  await expect(page.getByText('Полнота данных', { exact: true })).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '04-customer-card.png'), fullPage: true });

  // 5. Model Settings
  await page.getByRole('link', { name: 'Настройки модели', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Настройки риска' })).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '05-settings.png'), fullPage: true });

  // 6. Data management
  await page.getByRole('link', { name: 'Данные', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Снимок', exact: true })).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '06-data.png'), fullPage: true });

  // 7. Responsive 768px (Tablet) with navigation drawer
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto('/#/overview');
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '07-tablet-768.png'), fullPage: true });
  await page.getByRole('button', { name: 'Открыть меню' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(outDir, '08-drawer-768.png') });
  await page.keyboard.press('Escape');

  // 8. Responsive 360px (Mobile)
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/#/customers');
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '09-mobile-360.png'), fullPage: true });
});
