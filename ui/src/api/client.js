import axios from 'axios';
import { mockFetch } from './mock/index.js';

const useMock = import.meta.env.VITE_USE_MOCK !== 'false';
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const http = axios.create({ baseURL, timeout: 120000 });

export async function apiGet(path, options = {}) {
  if (useMock) {
    return mockFetch(path.replace(/^\//, ''), options);
  }
  const { data } = await http.get(path);
  return data;
}

export async function apiPost(path, body, options = {}) {
  if (useMock) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'POST', body });
  }
  const { data } = await http.post(path, body);
  return data;
}

function mapQueryResponseToMessage(payload, queryText) {
  const answer = payload?.answer ?? payload;
  return {
    id: `m-${Date.now()}`,
    role: 'assistant',
    content: answer?.summary ?? answer?.text ?? JSON.stringify(answer),
    expanded_synonyms: answer?.expanded_synonyms ?? [],
    confidence: answer?.confidence ?? null,
    sources: answer?.sources ?? payload?.sources ?? [],
    evidence_table: answer?.evidence_table ?? payload?.evidence_table,
    retrieval_trace: payload?.retrieval_trace ?? answer?.retrieval_trace,
  };
}

export async function submitChatQuery({ text, files }, { onStep, t } = {}) {
  if (useMock) {
    const { runMockChatQuery } = await import('./mock/chatQuery.js');
    return runMockChatQuery({ text, files }, { onStep, t, stepDelayMs: 650 });
  }
  const response = await apiPost('/api/query', {
    query: text,
    documents: [],
    limit: 20,
  });
  return mapQueryResponseToMessage(response, text);
}

export { useMock };
