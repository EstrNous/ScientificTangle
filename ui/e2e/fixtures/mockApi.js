const DIRECTOR_USER = {
  id: '00000000-0000-0000-0000-000000000003',
  username: 'director',
  email: 'director@example.com',
  role: 'manager',
  is_active: true,
};

const ACCESS_TOKEN = 'e2e-access-token';

function json(body, status = 200) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  };
}

function routeMatch(url, pattern) {
  const path = new URL(url).pathname;
  return path === pattern || path.startsWith(`${pattern}/`);
}

export function createMockState() {
  return {
    user: DIRECTOR_USER,
    interests: {
      raw_text: 'электроэкстракция никеля',
      interests: [{ label: 'электроэкстракция', weight: 1, source_terms: ['Ni'] }],
      extracted_entities: [{ name: 'никель', type: 'metal' }],
    },
    notifications: [
      {
        id: 'notif-1',
        type: 'ingestion_complete',
        title: 'Ingestion complete',
        reference_type: 'source_span',
        reference_id: 'span-public-1',
        read: false,
        created_at: new Date().toISOString(),
      },
    ],
    uploadTask: {
      id: 'task-e2e-1',
      status: 'completed',
      stages: [
        { id: 'parse', label: 'Parse', status: 'done', warnings: [] },
        { id: 'extract', label: 'Extract', status: 'done', warnings: ['minor table gap'] },
        { id: 'index', label: 'Index', status: 'done', warnings: [] },
      ],
      report: {
        normalized_documents: [{ id: 'doc-e2e-1', title: 'demo.pdf', metadata: {} }],
        documents_count: 1,
        source_spans_count: 5,
        extracted_claims_count: 3,
      },
    },
    reviewQueue: [
      {
        id: 'candidate-1',
        name: 'Ca/Mg ratio',
        type: 'numeric',
        status: 'pending',
        source_span_ids: ['span-public-1'],
        updated_at: new Date().toISOString(),
      },
    ],
    adminSnapshot: {
      users: [
        {
          id: 'user-1',
          username: 'researcher',
          name: 'researcher',
          email: 'researcher@example.com',
          role: 'researcher',
          is_active: true,
          active: true,
        },
      ],
      access_policies: [
        {
          id: 'policy-1',
          document_id: 'doc-e2e-1',
          title: 'demo.pdf',
          level: 'internal',
          export_allowed: true,
          roles: ['researcher', 'admin'],
        },
      ],
    },
    dictionaries: [
      {
        id: 'dict-v1',
        version: 'dictionary-package.v1',
        status: 'inactive',
        created_at: '2026-01-01T00:00:00Z',
        files: [{ name: 'terms.json' }],
      },
      {
        id: 'dict-v2',
        version: 'dictionary-package.v2',
        status: 'active',
        created_at: '2026-02-01T00:00:00Z',
        files: [{ name: 'terms.json' }, { name: 'aliases.json' }],
      },
    ],
    auditEvents: [
      {
        id: 'audit-1',
        action: 'query_created',
        timestamp: new Date().toISOString(),
        user: 'director',
        role: 'director',
        object: 'run-e2e-1',
        details: { query_run_id: 'run-e2e-1' },
      },
      {
        id: 'audit-2',
        action: 'document_exported',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        user: 'director',
        role: 'director',
        object: 'export-e2e-1',
        details: { query_run_id: 'run-e2e-1' },
      },
    ],
    searchResults: {
      items: [
        {
          source_span_id: 'span-public-1',
          document_id: 'doc-e2e-1',
          title: 'Шахтные воды',
          snippet: 'Ca/Mg 200-300 mg/l',
          score: 0.91,
        },
      ],
      total_found: 1,
      limit: 20,
      offset: 0,
    },
    sourcePublic: {
      id: 'span-public-1',
      document_id: 'doc-e2e-1',
      title: 'Шахтные воды',
      page: 2,
      highlight_start: 10,
      highlight_end: 28,
      raw_text: 'Содержание Ca/Mg в диапазоне 200-300 mg/l.',
      pages: [{ page: 2, text: 'Содержание Ca/Mg в диапазоне 200-300 mg/l.' }],
    },
    exportResult: {
      export_job_id: 'export-e2e-1',
      query_run_id: 'run-e2e-1',
      status: 'completed',
      format: 'json',
      content: '{"query_run":"run-e2e-1"}',
      content_type: 'application/json',
    },
  };
}

export async function installProductionApiMocks(page) {
  const state = createMockState();

  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const url = request.url();
    const method = request.method();

    if (routeMatch(url, '/api/auth/login') && method === 'POST') {
      await route.fulfill(json({ access_token: ACCESS_TOKEN, user: state.user }));
      return;
    }

    if (routeMatch(url, '/api/auth/me') && method === 'GET') {
      await route.fulfill(json(state.user));
      return;
    }

    if (routeMatch(url, '/api/chat/sessions') && method === 'GET') {
      await route.fulfill(json([]));
      return;
    }

    if (routeMatch(url, '/api/interests') && method === 'GET') {
      await route.fulfill(json(state.interests));
      return;
    }

    if (routeMatch(url, '/api/interests') && method === 'PUT') {
      const body = request.postDataJSON();
      state.interests.raw_text = body.raw_text ?? body.rawText ?? state.interests.raw_text;
      await route.fulfill(json(state.interests));
      return;
    }

    if (routeMatch(url, '/api/notifications') && method === 'GET') {
      await route.fulfill(json({ items: state.notifications }));
      return;
    }

    if (routeMatch(url, '/api/notifications/read-all') && method === 'POST') {
      state.notifications = state.notifications.map((item) => ({ ...item, read: true }));
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    if (url.includes('/api/notifications/') && url.endsWith('/read') && method === 'POST') {
      await route.fulfill({ status: 204, body: '' });
      return;
    }

    if (routeMatch(url, '/api/documents/upload') && method === 'POST') {
      await route.fulfill(json({ id: state.uploadTask.id }));
      return;
    }

    if (url.includes('/api/tasks/') && method === 'GET') {
      await route.fulfill(json(state.uploadTask));
      return;
    }

    if (routeMatch(url, '/api/source/span-locked-1') && method === 'GET') {
      await route.fulfill(json({ code: 'access_denied' }, 403));
      return;
    }

    if (url.includes('/api/source/') && method === 'GET') {
      await route.fulfill(json(state.sourcePublic));
      return;
    }

    if (routeMatch(url, '/api/export') && method === 'POST') {
      await route.fulfill(json(state.exportResult));
      return;
    }

    if (routeMatch(url, '/api/admin') && method === 'GET') {
      await route.fulfill(json(state.adminSnapshot));
      return;
    }

    if (url.includes('/api/admin/users/') && method === 'PATCH') {
      const saved = { ...state.adminSnapshot.users[0], ...request.postDataJSON() };
      await route.fulfill(json(saved));
      return;
    }

    if (url.includes('/api/admin/policies/') && method === 'PATCH') {
      await route.fulfill(json(state.adminSnapshot.access_policies[0]));
      return;
    }

    if (routeMatch(url, '/api/dictionaries') && method === 'GET') {
      await route.fulfill(json({ items: state.dictionaries }));
      return;
    }

    if (url.includes('/api/dictionaries/') && url.endsWith('/activate') && method === 'POST') {
      const versionId = url.split('/').slice(-2, -1)[0];
      state.dictionaries = state.dictionaries.map((item) => ({
        ...item,
        status: item.id === versionId ? 'active' : item.status === 'active' ? 'inactive' : item.status,
      }));
      const activated = state.dictionaries.find((item) => item.id === versionId);
      await route.fulfill(json(activated));
      return;
    }

    if (routeMatch(url, '/api/review/queue') && method === 'GET') {
      await route.fulfill(json({ items: state.reviewQueue, conflicts: [] }));
      return;
    }

    if (routeMatch(url, '/api/review/decisions') && method === 'POST') {
      state.reviewQueue = state.reviewQueue.map((item) =>
        item.id === 'candidate-1' ? { ...item, status: 'approved' } : item,
      );
      await route.fulfill(json({ status: 'accepted', item_id: 'candidate-1' }));
      return;
    }

    if (routeMatch(url, '/api/search') && method === 'GET') {
      await route.fulfill(json(state.searchResults));
      return;
    }

    if (routeMatch(url, '/api/audit/events') && method === 'GET') {
      const parsed = new URL(url);
      const action = parsed.searchParams.get('action');
      const items = action
        ? state.auditEvents.filter((event) => event.action === action)
        : state.auditEvents;
      await route.fulfill(json({ items }));
      return;
    }

    if (routeMatch(url, '/api/eval/report/summary') && method === 'GET') {
      await route.fulfill(
        json({
          status: 'pass',
          blocked_checks: ['live_answer_quality'],
          summary: { pass: 3, warn: 1, fail: 0 },
        }),
      );
      return;
    }

    await route.fulfill(json({ ok: true }));
  });
}

export async function loginThroughUi(page, { username = 'director', password = 'director123' } = {}) {
  await page.goto('/login');
  await page.getByLabel('Имя пользователя или email').fill(username);
  await page.getByLabel('Пароль', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Войти' }).click();
  await page.waitForURL('**/chat');
}
