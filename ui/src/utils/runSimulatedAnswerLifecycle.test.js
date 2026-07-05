import { describe, expect, it, vi } from 'vitest';
import { runSimulatedAnswerLifecycle } from './runSimulatedAnswerLifecycle.js';
import { CHAT_ANSWER_PHASES } from './chatAnswerLifecycle.js';

describe('runSimulatedAnswerLifecycle', () => {
  it('runs lifecycle phases and returns reply', async () => {
    const onPhaseChange = vi.fn();
    const onRetrievalStep = vi.fn();
    const t = (key) => key;

    const reply = await runSimulatedAnswerLifecycle(
      { text: 'никель', files: [] },
      {
        onPhaseChange,
        onRetrievalStep,
        t,
        phaseDelayMs: 0,
        stepDelayMs: 0,
      },
    );

    expect(reply.role).toBe('assistant');
    expect(reply.content).toContain('никель');
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.PARSING);
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.RETRIEVAL);
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.VERIFICATION);
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.SYNTHESIS);
    expect(onPhaseChange).toHaveBeenCalledWith(CHAT_ANSWER_PHASES.CITATIONS);
    expect(onRetrievalStep).toHaveBeenCalled();
  });
});
