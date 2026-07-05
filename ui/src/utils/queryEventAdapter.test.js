import { describe, expect, it, vi } from 'vitest';
import {
  applyQueryEvent,
  mapBackendPhase,
  mapRetrievalTraceFromResponse,
  normalizeQueryEvent,
} from './queryEventAdapter.js';
import { CHAT_ANSWER_PHASES } from './chatAnswerLifecycle.js';

describe('queryEventAdapter', () => {
  it('maps backend phase names', () => {
    expect(mapBackendPhase('retrieval')).toBe(CHAT_ANSWER_PHASES.RETRIEVAL);
    expect(mapBackendPhase('query_ir')).toBe(CHAT_ANSWER_PHASES.PARSING);
  });

  it('normalizes phase events', () => {
    expect(normalizeQueryEvent({ type: 'phase', phase: 'synthesis' })).toEqual({
      type: 'phase',
      phase: CHAT_ANSWER_PHASES.SYNTHESIS,
    });
  });

  it('normalizes answer chunk events', () => {
    expect(normalizeQueryEvent({ type: 'answer_chunk', chunk: 'partial', complete: false })).toEqual({
      type: 'answer_chunk',
      chunk: 'partial',
      complete: false,
    });
  });

  it('maps retrieval trace from response payload', () => {
    const trace = mapRetrievalTraceFromResponse(
      {
        retrieval_trace: {
          method: 'hybrid',
          retrieved: 3,
          files: ['a.pdf'],
          scopes: ['claims'],
        },
      },
      (key, params) => `${key}:${params.count}`,
    );
    expect(trace.steps).toHaveLength(4);
    expect(trace.completed).toBe(true);
  });

  it('applies events to handlers', () => {
    const onPhaseChange = vi.fn();
    const onStreamingDraft = vi.fn();
    const onStreamError = vi.fn();
    applyQueryEvent(
      { onPhaseChange, onStreamingDraft, onStreamError },
      { type: 'answer_chunk', chunk: 'text', complete: true },
    );
    expect(onStreamingDraft).toHaveBeenCalledWith('text', true);
    applyQueryEvent({ onPhaseChange, onStreamError }, { phase: 'verification' });
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.VERIFICATION);
    applyQueryEvent(
      { onPhaseChange, onStreamError },
      { type: 'phase', phase: 'error', code: 'query_stream_failed', message: 'failed' },
    );
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.ERROR);
    expect(onStreamError).toHaveBeenCalledWith({
      code: 'query_stream_failed',
      message: 'failed',
      status: null,
    });
  });
});
