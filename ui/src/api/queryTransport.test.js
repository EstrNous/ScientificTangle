import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { buildLifecycleEventsFromQueryRun, mapQueryRunToMessage, tryRunQueryEventStream } from './queryTransport.js';

vi.mock('./client.js', () => ({
  apiPost: vi.fn(),
}));

describe('queryTransport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
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

  it('posts SSE stream to api base path', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode('data: {"type":"phase","phase":"parsing"}\n\n'),
            })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    const events = [];
    const result = await tryRunQueryEventStream(
      { question: 'никель', authorization: 'Bearer token' },
      { onEvent: (event) => events.push(event) },
    );

    expect(result).toEqual({ ok: true, donePayload: null });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/query/stream',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Accept: 'text/event-stream',
          Authorization: 'Bearer token',
        }),
      }),
    );
    expect(events).toEqual([{ type: 'phase', phase: 'parsing' }]);
  });

  it('treats abort as graceful stream shutdown', async () => {
    const abortError = new DOMException('The operation was aborted.', 'AbortError');
    const fetchMock = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockRejectedValue(abortError),
        }),
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    await expect(
      tryRunQueryEventStream(
        { question: 'никель', authorization: 'Bearer token' },
        { signal: AbortSignal.abort() },
      ),
    ).resolves.toEqual({ ok: true, aborted: true });
  });

  it('logs and returns failReason when stream response is not ok', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const fetchMock = vi.fn(async () => ({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      body: null,
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    const result = await tryRunQueryEventStream(
      { question: 'никель', authorization: 'Bearer token' },
    );

    expect(warnSpy).toHaveBeenCalledWith(
      '[queryTransport] stream request failed',
      expect.objectContaining({ status: 503 }),
    );
    expect(result).toEqual({
      ok: false,
      failReason: {
        code: 'query_stream_failed',
        message: 'Service Unavailable',
        status: 503,
      },
    });
  });

  it('returns failReason when SSE emits phase error', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode(
                'data: {"type":"phase","phase":"error","code":"active_dictionary_required","message":"seed required"}\n\n',
              ),
            })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    const result = await tryRunQueryEventStream(
      { question: 'никель', authorization: 'Bearer token' },
    );

    expect(result).toEqual({
      ok: false,
      failReason: {
        code: 'active_dictionary_required',
        message: 'seed required',
        status: null,
      },
    });
  });

  it('returns donePayload when SSE stream completes', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({
              done: false,
              value: new TextEncoder().encode(
                'data: {"type":"done","payload":{"id":"run-1","answer":{"answer_text":"Ответ","confidence":0.8}}}\n\n',
              ),
            })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    const result = await tryRunQueryEventStream(
      { question: 'никель', authorization: 'Bearer token' },
    );

    expect(result.ok).toBe(true);
    expect(result.donePayload?.id).toBe('run-1');
  });

  it('logs and returns failReason when stream read throws', async () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const fetchMock = vi.fn(async () => ({
      ok: true,
      body: {
        getReader: () => ({
          read: vi.fn().mockRejectedValue(new Error('network reset')),
        }),
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_QUERY_STREAM_TRANSPORT', 'true');

    const result = await tryRunQueryEventStream(
      { question: 'никель', authorization: 'Bearer token' },
    );

    expect(warnSpy).toHaveBeenCalledWith(
      '[queryTransport] stream read failed',
      expect.objectContaining({ message: 'network reset' }),
    );
    expect(result).toEqual({
      ok: false,
      failReason: {
        code: 'query_stream_failed',
        message: 'network reset',
        status: null,
      },
    });
  });
});
