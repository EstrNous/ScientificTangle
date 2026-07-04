import axios from 'axios';
import { ensureAuth, authHeaders } from './auth.js';
import { mockFetch } from './mock/index.js';

const useMock = import.meta.env.VITE_USE_MOCK !== 'false';
const baseURL = import.meta.env.VITE_API_URL || '/api';

const http = axios.create({ baseURL, timeout: 120000 });

async function authorizedConfig(options = {}) {
  if (!options.real) return options;
  const token = await ensureAuth();
  return {
    ...options,
    headers: {
      ...options.headers,
      ...authHeaders(token),
    },
  };
}

export async function apiGet(path, options = {}) {
  if (useMock && !options.real) {
    return mockFetch(path.replace(/^\//, ''), options);
  }
  const { data } = await http.get(path, await authorizedConfig(options));
  return data;
}

export async function apiPost(path, body, options = {}) {
  if (useMock && !options.real) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'POST', body });
  }
  const response = await http.post(path, body, await authorizedConfig(options));
  if (response.status === 204) {
    return null;
  }
  return response.data;
}

export async function apiPut(path, body, options = {}) {
  if (useMock && !options.real) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'PUT', body });
  }
  const response = await http.put(path, body, await authorizedConfig(options));
  if (response.status === 204) {
    return null;
  }
  return response.data;
}

export async function apiPatch(path, body, options = {}) {
  if (useMock && !options.real) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'PATCH', body });
  }
  const response = await http.patch(path, body, await authorizedConfig(options));
  if (response.status === 204) {
    return null;
  }
  return response.data;
}

export async function apiDelete(path, options = {}) {
  if (useMock && !options.real) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'DELETE' });
  }
  const { data } = await http.delete(path, await authorizedConfig(options));
  return data;
}

function mapQueryResponseToMessage(payload) {
  const answer = payload?.answer ?? payload;
  return {
    id: `m-${Date.now()}`,
    role: 'assistant',
    content:
      answer?.short_answer ??
      answer?.summary ??
      answer?.text ??
      answer?.answer_text ??
      JSON.stringify(answer),
    expanded_synonyms: answer?.expanded_synonyms ?? payload?.expanded_synonyms ?? [],
    confidence: answer?.confidence ?? payload?.confidence ?? null,
    sources: answer?.sources ?? payload?.sources ?? [],
    evidence_table: answer?.evidence_table ?? payload?.evidence_table,
    retrieval_trace: payload?.retrieval_trace ?? answer?.retrieval_trace,
    scientific_answer: answer?.scientific_answer ?? payload?.scientific_answer ?? null,
    warnings: answer?.warnings ?? payload?.warnings ?? [],
  };
}

export async function submitChatQuery({ text, files }, { onStep, onEvent, t } = {}) {
  if (useMock) {
    const { runMockChatQuery } = await import('./mock/chatQuery.js');
    return runMockChatQuery({ text, files }, { onStep, t, stepDelayMs: 650 });
  }
  const { runLiveQueryTransport } = await import('./queryTransport.js');
  const { applyQueryEvent } = await import('../utils/queryEventAdapter.js');
  return runLiveQueryTransport(
    { question: text },
    {
      t,
      revealAnswer: false,
      onEvent: (event) => {
        onEvent?.(event);
        if (event.type === 'retrieval_step' || event.steps) {
          onStep?.({
            steps: event.steps ?? [],
            activeStepId: event.activeStepId ?? null,
            completed: Boolean(event.completed),
          });
        }
        applyQueryEvent(
          {
            onRetrievalStep: onStep,
          },
          event,
        );
      },
    },
  );
}

export { useMock };

export function apiOptions() {
  return useMock ? {} : { real: true };
}
