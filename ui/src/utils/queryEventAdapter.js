import { CHAT_ANSWER_PHASES } from './chatAnswerLifecycle.js';

export const QUERY_EVENT_TYPES = {
  PHASE: 'phase',
  RETRIEVAL_STEP: 'retrieval_step',
  ANSWER_CHUNK: 'answer_chunk',
  DONE: 'done',
};

const BACKEND_PHASE_MAP = {
  parsing: CHAT_ANSWER_PHASES.PARSING,
  query_ir: CHAT_ANSWER_PHASES.PARSING,
  retrieval: CHAT_ANSWER_PHASES.RETRIEVAL,
  verification: CHAT_ANSWER_PHASES.VERIFICATION,
  synthesis: CHAT_ANSWER_PHASES.SYNTHESIS,
  citations: CHAT_ANSWER_PHASES.CITATIONS,
  done: CHAT_ANSWER_PHASES.DONE,
  degraded: CHAT_ANSWER_PHASES.DEGRADED,
  error: CHAT_ANSWER_PHASES.ERROR,
};

export function mapBackendPhase(value) {
  if (!value) return null;
  const key = String(value).toLowerCase();
  return BACKEND_PHASE_MAP[key] ?? null;
}

export function normalizeQueryEvent(event) {
  if (!event || typeof event !== 'object') return null;

  if (event.type === QUERY_EVENT_TYPES.PHASE || event.phase) {
    const phase = mapBackendPhase(event.phase ?? event.name);
    if (!phase) return null;
    return { type: QUERY_EVENT_TYPES.PHASE, phase };
  }

  if (event.type === QUERY_EVENT_TYPES.RETRIEVAL_STEP || event.steps) {
    return {
      type: QUERY_EVENT_TYPES.RETRIEVAL_STEP,
      trace: {
        steps: event.steps ?? [],
        activeStepId: event.activeStepId ?? null,
        completed: Boolean(event.completed),
      },
    };
  }

  if (event.type === QUERY_EVENT_TYPES.ANSWER_CHUNK || event.chunk != null) {
    const chunk = event.chunk ?? event.text ?? '';
    return {
      type: QUERY_EVENT_TYPES.ANSWER_CHUNK,
      chunk: String(chunk),
      complete: Boolean(event.complete),
    };
  }

  if (event.type === QUERY_EVENT_TYPES.DONE) {
    return { type: QUERY_EVENT_TYPES.DONE, payload: event.payload ?? null };
  }

  return null;
}

export function mapRetrievalTraceFromResponse(payload, t) {
  const trace = payload?.retrieval_trace;
  if (!trace || typeof trace !== 'object') return null;

  const steps = [];
  if (trace.method) {
    steps.push({
      id: 'method',
      label: trace.method,
      status: 'done',
    });
  }

  const files = trace.files ?? trace.documents ?? [];
  files.forEach((file, index) => {
    steps.push({
      id: `file-${index}`,
      label: typeof file === 'string' ? file : file.name ?? `source-${index}`,
      status: 'done',
    });
  });

  if (trace.retrieved != null) {
    steps.push({
      id: 'retrieved',
      label: t
        ? t('chat.retrieval.retrievedCount', { count: trace.retrieved })
        : `retrieved: ${trace.retrieved}`,
      status: 'done',
    });
  }

  if (trace.scopes?.length) {
    steps.push({
      id: 'scopes',
      label: trace.scopes.join(', '),
      status: 'done',
    });
  }

  if (!steps.length) return null;
  return { steps, activeStepId: null, completed: true };
}

export function applyQueryEvent(handlers, event) {
  const normalized = normalizeQueryEvent(event);
  if (!normalized) return;

  if (normalized.type === QUERY_EVENT_TYPES.PHASE) {
    handlers.onPhaseChange?.(normalized.phase);
    if (normalized.phase === CHAT_ANSWER_PHASES.ERROR) {
      handlers.onStreamError?.({
        code: event.code ?? event.error_code ?? null,
        message: event.message ?? event.error ?? null,
        status: event.status ?? null,
      });
    }
    return;
  }

  if (normalized.type === QUERY_EVENT_TYPES.RETRIEVAL_STEP) {
    handlers.onRetrievalStep?.(normalized.trace);
    return;
  }

  if (normalized.type === QUERY_EVENT_TYPES.ANSWER_CHUNK) {
    handlers.onStreamingDraft?.(normalized.chunk, normalized.complete);
    return;
  }

  if (normalized.type === QUERY_EVENT_TYPES.DONE) {
    handlers.onDone?.(normalized.payload);
  }
}
