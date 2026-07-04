import ingestion from './ingestion.json';
import audit from './audit.json';
import admin from './admin.json';
import notificationsSeed from './notifications.json';
import interestsSeed from './interests.json';
import reviewSeed from './review.json';

let notificationItems = notificationsSeed.items.map((item) => ({ ...item }));
let interestsProfile = { ...interestsSeed, interests: [...interestsSeed.interests] };
let reviewQueue = {
  items: reviewSeed.items.map((item) => ({ ...item })),
  total: reviewSeed.total,
};
let adminSnapshot = JSON.parse(JSON.stringify(admin));

export const mockData = {
  ingestion,
  audit,
  admin: adminSnapshot,
  notifications: { items: notificationItems },
  interests: interestsProfile,
  review: reviewQueue,
};

export async function mockFetch(resource, options = {}) {
  await delay(options.delay ?? 200);

  if (resource.startsWith('chat/')) {
    throw new Error('Chat API requires backend connection');
  }
  if (resource === 'graph' || resource.startsWith('graph/')) {
    throw new Error('Graph API requires backend connection');
  }
  if (resource === 'search' || resource === 'lab/search') {
    throw new Error('Search API requires backend connection');
  }
  if (resource === 'strategic/metrics' || resource === 'strategic/evaluation' || resource.startsWith('strategic/')) {
    throw new Error('Strategic API requires backend connection');
  }
  if (resource === 'lab/coverage' || resource.startsWith('lab/')) {
    throw new Error('Lab API requires backend connection');
  }
  if (resource === 'ingestion/tasks') {
    return ingestion.tasks;
  }
  if (resource === 'audit/events') {
    return audit.events;
  }
  if (resource === 'admin') {
    return adminSnapshot;
  }
  if (resource === 'interests' && options.method === 'PUT') {
    const body = options.body ?? {};
    interestsProfile = {
      ...interestsProfile,
      raw_text: body.raw_text ?? interestsProfile.raw_text,
      interests: body.interests ?? interestsProfile.interests,
      updated_at: new Date().toISOString(),
    };
    return { ...interestsProfile, interests: interestsProfile.interests.map((item) => ({ ...item })) };
  }
  if (resource === 'interests') {
    return {
      ...interestsProfile,
      interests: interestsProfile.interests.map((item) => ({ ...item })),
    };
  }
  if (resource === 'review/queue' || resource.startsWith('review/queue?')) {
    const query = resource.includes('?') ? resource.split('?')[1] : '';
    const params = Object.fromEntries(new URLSearchParams(query));
    const body = options.method === 'POST' ? (options.body ?? {}) : params;
    let items = reviewQueue.items.map((item) => ({ ...item }));
    if (body.status) {
      items = items.filter((item) => item.status === body.status);
    }
    if (body.type) {
      items = items.filter((item) => item.type === body.type);
    }
    return { items, total: items.length, filters: body };
  }
  if (resource === 'review/decisions') {
    const body = options.body ?? {};
    reviewQueue.items = reviewQueue.items.map((item) =>
      item.id === body.candidate_id ? { ...item, status: body.decision ?? 'approved' } : item,
    );
    return {
      candidate_id: body.candidate_id,
      decision: body.decision,
      status: 'accepted',
      audit_event_id: 'audit-review-mock-001',
    };
  }
  if (resource === 'export') {
    const body = options.body ?? {};
    const format = body.format ?? 'markdown';
    return {
      export_job_id: '00000000-0000-4000-8000-0000000000e1',
      query_run_id: body.query_run_id,
      format,
      status: 'completed',
      content_type: format === 'json' ? 'application/json' : 'text/markdown',
      content: format === 'json' ? { query_run_id: body.query_run_id } : '# Mock export',
      file_url: '',
      warnings: [],
      generated_at: new Date().toISOString(),
    };
  }
  if (resource.startsWith('admin/users/') && options.method === 'PATCH') {
    const userId = resource.slice('admin/users/'.length);
    const body = options.body ?? {};
    adminSnapshot.users = adminSnapshot.users.map((user) =>
      user.id === userId
        ? {
            ...user,
            role: body.role ?? user.role,
            active: body.active ?? body.is_active ?? user.active,
          }
        : user,
    );
    return adminSnapshot.users.find((user) => user.id === userId);
  }
  if (resource.startsWith('admin/policies/') && options.method === 'PATCH') {
    const documentId = resource.slice('admin/policies/'.length);
    const policyPatch = options.body?.access_policy ?? {};
    adminSnapshot.access_policies = adminSnapshot.access_policies.map((policy) =>
      policy.id === documentId
        ? {
            ...policy,
            level: policyPatch.level ?? policy.level,
            export_allowed: policyPatch.export_allowed ?? policy.export_allowed,
            roles: policyPatch.roles ?? policy.roles,
          }
        : policy,
    );
    return adminSnapshot.access_policies.find((policy) => policy.id === documentId);
  }
  if (resource.startsWith('documents/') && options.method === 'DELETE') {
    const documentId = resource.slice('documents/'.length);
    return {
      document_id: documentId,
      status: 'deleted',
      tombstone_id: `tombstone-${documentId}`,
      warnings: [],
    };
  }
  if (resource.startsWith('notifications') && resource.includes('?since=')) {
    const since = decodeURIComponent(resource.split('?since=')[1] ?? '');
    return notificationItems
      .filter((item) => item.created_at > since)
      .map((item) => ({ ...item }));
  }
  if (resource === 'notifications') {
    return notificationItems.map((item) => ({ ...item }));
  }
  if (resource === 'notifications/read-all') {
    notificationItems = notificationItems.map((item) => ({ ...item, read: true }));
    return { ok: true };
  }
  if (resource.startsWith('notifications/') && resource.endsWith('/read')) {
    const id = resource.slice('notifications/'.length, -'/read'.length);
    notificationItems = notificationItems.map((item) =>
      item.id === id ? { ...item, read: true } : item,
    );
    return { ok: true };
  }
  if (resource === 'api/query' || resource === 'query') {
    const { runMockChatQuery } = await import('./chatQuery.js');
    const body = options.body ?? {};
    return runMockChatQuery(
      { text: body.query ?? '', files: [] },
      { t: (key, params) => key, stepDelayMs: 0 },
    );
  }

  throw new Error(`Mock resource not found: ${resource}`);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
