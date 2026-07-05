import { test, expect } from '@playwright/test';
import {
  EXTERNAL_PARTNER_USER,
  installProductionApiMocks,
  loginThroughUi,
} from './fixtures/mockApi.js';

async function expectNoInterfaceError(page) {
  await expect(page.getByText('Ошибка интерфейса')).not.toBeVisible();
}

test.describe('E6 no-live UI scenarios @offline', () => {
  test.beforeEach(async ({ page }) => {
    await installProductionApiMocks(page);
    await loginThroughUi(page);
  });

  test('scenario 1: interests save on profile', async ({ page }) => {
    await page.goto('/profile');
    await page.getByRole('button', { name: 'Редактировать' }).first().click();
    const textarea = page.getByPlaceholder(/электроэкстракция/i);
    await textarea.fill('циркуляция католита, обессоливание шахтных вод');
    await page.getByRole('button', { name: 'Сохранить интересы' }).click();
    await expect(page.getByText('Интересы сохранены')).toBeVisible();
  });

  test('scenario 1b: upload page renders without interface error', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.getByText('Ошибка интерфейса')).not.toBeVisible();
  });

  test('scenario 2: upload stages visible after upload', async ({ page }) => {
    await page.goto('/upload');
    const pdf = {
      name: 'demo.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 demo'),
    };
    await page.locator('input[type="file"]').first().setInputFiles(pdf);
    await page.getByRole('button', { name: 'Загрузить' }).click();
    await expect(page.getByText('Этапы обработки')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('minor table gap')).toBeVisible();
  });

  test('scenario 2b: upload adds ingestion_complete notification to bell', async ({ page }) => {
    await page.goto('/upload');
    const pdf = {
      name: 'demo.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 demo'),
    };
    await page.locator('input[type="file"]').first().setInputFiles(pdf);
    await page.getByRole('button', { name: 'Загрузить' }).click();
    await expect(page.getByText('Этапы обработки')).toBeVisible({ timeout: 15000 });
    await page.getByRole('button', { name: 'Уведомления' }).click();
    await expect(page.getByRole('button', { name: 'Обработка документа завершена' })).toBeVisible();
  });

  test('scenario 3: notification click opens source viewer', async ({ page }) => {
    await page.goto('/chat');
    await page.getByRole('button', { name: 'Уведомления' }).click();
    await page.getByRole('button', { name: 'Обработка документа завершена' }).click();
    await expect(page.getByText('Шахтные воды')).toBeVisible();
  });

  test('scenario 4a: source highlight on review console', async ({ page }) => {
    await page.goto('/review');
    await page.getByRole('cell', { name: 'Ca/Mg ratio' }).click();
    await expect(page.getByText('Шахтные воды')).toBeVisible();
    await expect(page.getByText('200-300 mg/l')).toBeVisible();
  });

  test('scenario 4b: source locked 403 state', async ({ page }) => {
    await page.route('**/api/source/**', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ code: 'access_denied' }),
      }),
    );
    await page.goto('/review');
    await page.getByRole('cell', { name: 'Ca/Mg ratio' }).click();
    await expect(page.getByText('Источник недоступен')).toBeVisible();
  });

  test('scenario 5: export panel shows server formats and unavailable JSON-LD', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.getByRole('button', { name: 'Скачать JSON' })).toBeVisible();
    await expect(page.getByRole('button', { name: /Скачать MD/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Скачать JSON-LD/i })).toBeDisabled();
  });

  test('scenario 5c: new chat creates session in history', async ({ page }) => {
    await page.goto('/chat');
    await page.getByRole('button', { name: 'Новый чат' }).first().click();
    await expect(page.getByRole('button', { name: 'Новый запрос' })).toBeVisible();
    await expect(page.getByText('Задайте вопрос, чтобы начать диалог')).toBeVisible();
  });

  test('scenario 6: admin save all persists dirty rows', async ({ page }) => {
    await page.goto('/admin');
    const roleSelect = page.locator('select').first();
    await roleSelect.selectOption('analyst');
    await page.getByRole('button', { name: /Сохранить все/i }).click();
    await expect(page.getByText('Изменения сохранены')).toBeVisible();
  });

  test('scenario 7: review decision approves candidate', async ({ page }) => {
    await page.goto('/review');
    await page.getByRole('cell', { name: 'Ca/Mg ratio' }).click();
    await page.getByRole('button', { name: 'Подтвердить' }).click();
    await expect(page.getByText('подтверждён')).toBeVisible();
  });

  test('scenario 8: search filters submit query', async ({ page }) => {
    await page.goto('/search');
    await page.getByPlaceholder('Поиск по узлам, материалам и публикациям').fill('шахтные воды Ca/Mg');
    await page.getByPlaceholder('Россия, Norilsk').fill('Норильск');
    await page.getByPlaceholder('2020').fill('2020');
    await page.getByPlaceholder('2026').fill('2026');
    await page.locator('form button[type="submit"]').click();
    await expect(page.getByText('Шахтные воды')).toBeVisible();
  });

  test('scenario 9: dictionary activate action', async ({ page }) => {
    await page.goto('/admin');
    await page.getByRole('button', { name: 'Активировать' }).first().click();
    await expect(page.getByText('dictionary-package.v1')).toBeVisible();
  });

  test('scenario 10: audit filtering by action', async ({ page }) => {
    await page.goto('/admin/audit');
    await page.locator('select').first().selectOption('document_exported');
    await expect(page.getByText('экспорт')).toBeVisible();
    await expect(page.getByText('запрос')).not.toBeVisible();
  });
});

test.describe('E6 wave1 route smoke @offline', () => {
  test.beforeEach(async ({ page }) => {
    await installProductionApiMocks(page);
    await loginThroughUi(page);
  });

  test('smoke: graph page renders', async ({ page }) => {
    await page.goto('/graph');
    await expect(page.getByText('Карта знаний')).toBeVisible({ timeout: 15000 });
    await expectNoInterfaceError(page);
  });

  test('smoke: strategic coverage page renders', async ({ page }) => {
    await page.goto('/strategic/coverage');
    await expect(page.getByText('Покрытие базы знаний')).toBeVisible({ timeout: 15000 });
    await expectNoInterfaceError(page);
  });

  test('smoke: lab matrix page renders', async ({ page }) => {
    await page.goto('/lab/matrix');
    await expect(page.getByText('Матрица связей')).toBeVisible({ timeout: 15000 });
    await expectNoInterfaceError(page);
  });

  test('smoke: search page renders', async ({ page }) => {
    await page.goto('/search');
    await expect(page.getByPlaceholder('Поиск по узлам, материалам и публикациям')).toBeVisible();
    await expectNoInterfaceError(page);
  });

  test('smoke: top bar locale toggle RU/EN', async ({ page }) => {
    await page.goto('/chat');
    await expect(page.getByText('НорСинтез')).toBeVisible();
    await page.getByRole('button', { name: 'EN' }).click();
    await expect(page.getByRole('button', { name: 'RU' })).toBeVisible();
    await expect(page.getByText('NorSintez')).toBeVisible();
    await expectNoInterfaceError(page);
  });
});

test.describe('E6 wave1 register smoke @offline', () => {
  test.beforeEach(async ({ page }) => {
    await installProductionApiMocks(page);
  });

  test('smoke: register page renders', async ({ page }) => {
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: 'Регистрация' })).toBeVisible();
    await expectNoInterfaceError(page);
  });
});

test.describe('E6 wave1 access denied @offline', () => {
  test('smoke: external_partner upload shows access denied', async ({ page }) => {
    await installProductionApiMocks(page, { user: EXTERNAL_PARTNER_USER });
    await loginThroughUi(page, { username: 'external_partner' });
    await page.goto('/upload');
    await expect(page.getByText('Нет доступа к этой странице')).toBeVisible();
    await expectNoInterfaceError(page);
  });
});

test('production build loads login without mock role switcher @offline', async ({ page }) => {
  await installProductionApiMocks(page);
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Вход' })).toBeVisible();
});
