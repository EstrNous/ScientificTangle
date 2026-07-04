import { apiPost } from './client.js';
import { mapSourcePayload } from './source.js';
import { CHAT_ANSWER_PHASES } from '../utils/chatAnswerLifecycle.js';
import {
  applyQueryEvent,
  mapRetrievalTraceFromResponse,
} from '../utils/queryEventAdapter.js';
import { revealMarkdownText } from '../utils/growingMarkdown.js';
import { normalizeWarnings, pickScientificFields } from '../utils/answerPayload.js';

const STREAM_PATH = import.meta.env.VITE_QUERY_STREAM_PATH || '/query/stream';

export function isQueryStreamTransportAvailable() {
  return import.meta.env.VITE_QUERY_STREAM_TRANSPORT === 'true';
}

export function mapQueryRunToMessage(payload, t) {
  const answer = payload?.answer ?? {};
  const evidenceBundle = payload?.evidence_bundle ?? answer?.evidence_bundle ?? {};
  const evidenceItems = evidenceBundle?.evidence_items ?? [];
  const queryIr = payload?.query_ir ?? answer?.query_ir ?? {};

  const sources = [];
  const rows = [];
  for (const item of evidenceItems) {
    const span = item?.source_span ?? {};
    const spanId = span.id ?? span.document_id ?? 'source';
    const documentId = span.document_id ?? 'source';
    const snippet = (span.text ?? '').trim();
    sources.push({
      title: documentId,
      author: documentId,
      date: '',
      confidence_level: 'verified',
      source_span_id: spanId,
    });
    if (snippet) {
      rows.push([`Стр. ${span.page ?? '—'}`, snippet.slice(0, 160), spanId]);
    }
  }

  const scientificSource = answer?.scientific_answer ?? payload?.scientific_answer ?? null;
  const scientificAnswer =
    scientificSource && typeof scientificSource === 'object'
      ? pickScientificFields(scientificSource)
      : null;

  const content =
    scientificAnswer?.short_answer ??
    answer?.answer_text ??
    answer?.summary ??
    answer?.text ??
    '';

  return {
    id: payload?.id ? `run-${payload.id}` : `m-${Date.now()}`,
    role: 'assistant',
    content: content || 'Ответ не сформирован.',
    expanded_synonyms: queryIr?.entities ?? payload?.expanded_synonyms ?? [],
    confidence: answer?.confidence ?? payload?.confidence ?? null,
    sources,
    evidence_table: {
      columns: ['Параметр', 'Фрагмент', 'Источник'],
      rows: rows.slice(0, 8),
    },
    retrieval_trace: payload?.retrieval_trace ?? answer?.retrieval_trace ?? null,
    scientific_answer: scientificAnswer,
    warnings: normalizeWarnings(payload?.warnings ?? answer?.warnings ?? []),
    query_run_id: payload?.id ?? null,
  };
}

export function buildLifecycleEventsFromQueryRun(payload, t) {
  const events = [
    { type: 'phase', phase: 'parsing' },
    { type: 'phase', phase: 'retrieval' },
  ];

  const trace = mapRetrievalTraceFromResponse(
    { retrieval_trace: payload?.retrieval_trace },
    t,
  );
  if (trace) {
    events.push({
      type: 'retrieval_step',
      steps: trace.steps,
      completed: true,
    });
  }

  events.push(
    { type: 'phase', phase: 'verification' },
    { type: 'phase', phase: 'synthesis' },
  );

  const message = mapQueryRunToMessage(payload, t);
  if (message.content) {
    events.push({ type: 'answer_chunk', chunk: message.content, complete: true });
  }

  events.push({ type: 'phase', phase: 'citations' });
  return { events, message };
}

export async function runLiveQueryTransport(
  { question },
  { t, onEvent, revealAnswer = true, chunkDelayMs = 25 } = {},
) {
  const payload = await apiPost(
    '/query',
    { question, filters: {}, limit: 20 },
    { real: true },
  );

  const { events, message } = buildLifecycleEventsFromQueryRun(payload, t);
  const handlers = {
    onPhaseChange: (phase) => onEvent?.({ type: 'phase', phase }),
    onRetrievalStep: (trace) => onEvent?.({ type: 'retrieval_step', ...trace }),
    onStreamingDraft: (chunk, complete) => onEvent?.({ type: 'answer_chunk', chunk, complete }),
  };

  for (const event of events) {
    if (event.type === 'answer_chunk' && revealAnswer && !event.complete) {
      await revealMarkdownText(event.chunk, {
        onReveal: (partial) => handlers.onStreamingDraft?.(partial, false),
        chunkDelayMs,
      });
      handlers.onStreamingDraft?.(event.chunk, true);
      continue;
    }
    if (event.type === 'answer_chunk' && revealAnswer && event.complete) {
      await revealMarkdownText(event.chunk, {
        onReveal: (partial) => handlers.onStreamingDraft?.(partial, false),
        chunkDelayMs,
      });
      handlers.onStreamingDraft?.(event.chunk, true);
      continue;
    }
    applyQueryEvent(handlers, event);
  }

  const terminalPhase =
    message.confidence != null && message.confidence < 0.6
      ? CHAT_ANSWER_PHASES.DEGRADED
      : CHAT_ANSWER_PHASES.DONE;
  handlers.onPhaseChange?.(terminalPhase);

  return { ...message, lifecycle: terminalPhase };
}

export async function tryRunQueryEventStream(
  { question, authorization },
  { onEvent, signal } = {},
) {
  if (!isQueryStreamTransportAvailable()) {
    return null;
  }

  const response = await fetch(STREAM_PATH, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: authorization,
    },
    body: JSON.stringify({ question, filters: {}, limit: 20 }),
    signal,
  });

  if (!response.ok || !response.body) {
    return null;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const part of parts) {
      const dataLine = part
        .split('\n')
        .find((line) => line.startsWith('data:'));
      if (!dataLine) continue;
      const raw = dataLine.slice(5).trim();
      if (!raw) continue;
      try {
        const event = JSON.parse(raw);
        onEvent?.(event);
      } catch {
        continue;
      }
    }
  }

  return true;
}
