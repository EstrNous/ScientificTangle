import chat from './chat.json';
import graph from './graph.json';
import ingestion from './ingestion.json';
import strategic from './strategic.json';
import lab from './lab.json';
import audit from './audit.json';
import notifications from './notifications.json';

export const mockData = {
  chat,
  graph,
  ingestion,
  strategic,
  lab,
  audit,
  notifications,
};

export async function mockFetch(resource, options = {}) {
  await delay(options.delay ?? 200);

  if (resource === 'chat/sessions') {
    return chat.sessions;
  }
  if (resource.startsWith('chat/sessions/') && resource.endsWith('/messages')) {
    return chat.messages;
  }
  if (resource === 'graph') {
    return graph;
  }
  if (resource === 'graph/subgraph') {
    return graph.subgraph;
  }
  if (resource === 'ingestion/tasks') {
    return ingestion.tasks;
  }
  if (resource === 'strategic/metrics') {
    return strategic.manager;
  }
  if (resource === 'strategic/evaluation') {
    return strategic.evaluation;
  }
  if (resource === 'lab/coverage') {
    return lab;
  }
  if (resource === 'lab/search') {
    return lab.searchResults;
  }
  if (resource === 'audit/events') {
    return audit.events;
  }
  if (resource === 'notifications') {
    return notifications.items;
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
