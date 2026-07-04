import { describe, expect, it, vi, beforeEach } from 'vitest';
import { buildLifecycleEventsFromQueryRun, mapQueryRunToMessage } from './queryTransport.js';

vi.mock('./client.js', () => ({
  apiPost: vi.fn(),
}));

describe('queryTransport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('maps query run payload to assistant message', () => {
    const message = mapQueryRunToMessage(
      {
        id: 'run-1',
        retrieval_trace: { method: 'hybrid', retrieved: 2 },
        answer: {
          answer_text: 'Краткий ответ',
          confidence: 0.9,
          evidence_bundle: {
            evidence_items: [
              {
                source_span: {
                  id: 'span-1',
                  document_id: 'doc-1',
                  text: 'фрагмент',
                  page: 3,
                },
              },
            ],
          },
        },
        warnings: ['warn'],
      },
      (key, params) => `${key}:${params?.count ?? ''}`,
    );

    expect(message.role).toBe('assistant');
    expect(message.content).toBe('Краткий ответ');
    expect(message.sources).toHaveLength(1);
    expect(message.retrieval_trace.method).toBe('hybrid');
  });

  it('builds lifecycle events from query run', () => {
    const { events, message } = buildLifecycleEventsFromQueryRun(
      {
        retrieval_trace: { method: 'hybrid' },
        answer: { answer_text: 'Ответ', confidence: 0.8 },
      },
      (key) => key,
    );

    expect(events.some((event) => event.phase === 'retrieval')).toBe(true);
    expect(message.content).toBe('Ответ');
    expect(events.some((event) => event.type === 'answer_chunk')).toBe(true);
  });
});
