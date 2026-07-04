import { test } from '@playwright/test';

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
    await page.goto(`${stackBaseUrl}/login`);
    await page.getByLabel('Имя пользователя или email').fill('researcher');
    await page.getByLabel('Пароль', { exact: true }).fill('researcher123');
    await page.getByRole('button', { name: 'Войти' }).click();
    await page.waitForURL('**/chat');
    await page.goto(`${stackBaseUrl}/profile`);
    await page.getByText('Профиль интересов').waitFor();
  });
});
