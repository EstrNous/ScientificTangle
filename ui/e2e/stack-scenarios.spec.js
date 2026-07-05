import { test, expect } from '@playwright/test';

const stackBaseUrl = process.env.E2E_STACK_URL || 'http://127.0.0.1:3000';
const gatewayHealth = process.env.E2E_GATEWAY_HEALTH_URL || 'http://127.0.0.1:8000/health';

async function isStackAvailable() {
  try {
    const response = await fetch(gatewayHealth, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}

async function loginStackUser(page) {
  await page.goto(`${stackBaseUrl}/login`);
  await page.getByLabel('Имя пользователя или email').fill('researcher');
  await page.getByLabel('Пароль', { exact: true }).fill('researcher123');
  await page.getByRole('button', { name: 'Войти' }).click();
  await page.waitForURL('**/chat');
}

test.describe('E6 stack-backed smoke @stack', () => {
  test.beforeEach(async ({}, testInfo) => {
    if (process.env.RUN_UI_E2E !== '1') {
      testInfo.skip(true, 'RUN_UI_E2E=1 required for stack-backed UI e2e');
    }
    if (!(await isStackAvailable())) {
      testInfo.skip(true, `stack unavailable at ${gatewayHealth}`);
    }
  });

  test('login and open profile in production mode', async ({ page }) => {
    await loginStackUser(page);
    await page.goto(`${stackBaseUrl}/profile`);
    await page.getByText('Профиль интересов').waitFor();
  });

  test('open upload page', async ({ page }) => {
    await loginStackUser(page);
    await page.goto(`${stackBaseUrl}/upload`);
    await expect(page.getByText('Перетащите файлы сюда')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Ошибка интерфейса')).not.toBeVisible();
  });

  test('optional small file upload', async ({ page }) => {
    await loginStackUser(page);
    await page.goto(`${stackBaseUrl}/upload`);
    const pdf = {
      name: 'stack-smoke.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 stack-smoke'),
    };
    await page.locator('input[type="file"]').first().setInputFiles(pdf);
    await page.getByRole('button', { name: 'Загрузить' }).click();
    await expect(page.getByText('Этапы обработки')).toBeVisible({ timeout: 60000 });
  });
});
