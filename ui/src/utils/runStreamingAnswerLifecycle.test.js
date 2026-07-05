import { describe, expect, it, vi } from 'vitest';
import { runStreamingAnswerLifecycle } from './runStreamingAnswerLifecycle.js';
import { CHAT_ANSWER_PHASES } from './chatAnswerLifecycle.js';

describe('runStreamingAnswerLifecycle', () => {
  it('streams draft text during synthesis', async () => {
    const onPhaseChange = vi.fn();
    const onStreamingDraft = vi.fn();
    const t = (key) => key;

    const reply = await runStreamingAnswerLifecycle(
      { text: 'никель', files: [] },
      {
        onPhaseChange,
        onStreamingDraft,
        t,
        phaseDelayMs: 0,
        stepDelayMs: 0,
        chunkDelayMs: 0,
      },
    );

    expect(reply.role).toBe('assistant');
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.SYNTHESIS);
    expect(onStreamingDraft.mock.calls.length).toBeGreaterThan(1);
    expect(onStreamingDraft).toHaveBeenCalledWith(expect.any(String), true);
  });
});
