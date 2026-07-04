import ingestion from './ingestion.json';
import audit from './audit.json';
import admin from './admin.json';
import notificationsSeed from './notifications.json';

let notificationItems = notificationsSeed.items.map((item) => ({ ...item }));

export const mockData = {
  ingestion,
  audit,
  admin,
  notifications: { items: notificationItems },
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
    return admin;
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
