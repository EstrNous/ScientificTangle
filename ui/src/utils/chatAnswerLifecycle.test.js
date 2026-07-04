import { describe, expect, it } from 'vitest';
import {
  CHAT_ANSWER_PHASES,
  canTransitionPhase,
  isTerminalPhase,
  phaseIndex,
  resolveAnswerPhase,
  shouldShowAnswerPipeline,
  shouldShowRetrievalTrace,
  transitionPhase,
} from './chatAnswerLifecycle.js';

describe('chatAnswerLifecycle', () => {
  it('allows pipeline transitions', () => {
    expect(
      canTransitionPhase(CHAT_ANSWER_PHASES.PARSING, CHAT_ANSWER_PHASES.RETRIEVAL),
    ).toBe(true);
    expect(
      canTransitionPhase(CHAT_ANSWER_PHASES.RETRIEVAL, CHAT_ANSWER_PHASES.VERIFICATION),
    ).toBe(true);
    expect(
      canTransitionPhase(CHAT_ANSWER_PHASES.CITATIONS, CHAT_ANSWER_PHASES.DONE),
    ).toBe(true);
  });

  it('blocks invalid transitions', () => {
    expect(
      canTransitionPhase(CHAT_ANSWER_PHASES.PARSING, CHAT_ANSWER_PHASES.CITATIONS),
    ).toBe(false);
    expect(canTransitionPhase(CHAT_ANSWER_PHASES.DONE, CHAT_ANSWER_PHASES.PARSING)).toBe(false);
  });

  it('transitions only when allowed', () => {
    expect(
      transitionPhase(CHAT_ANSWER_PHASES.PARSING, CHAT_ANSWER_PHASES.RETRIEVAL),
    ).toBe(CHAT_ANSWER_PHASES.RETRIEVAL);
    expect(
      transitionPhase(CHAT_ANSWER_PHASES.PARSING, CHAT_ANSWER_PHASES.CITATIONS),
    ).toBe(CHAT_ANSWER_PHASES.PARSING);
  });

  it('marks terminal phases', () => {
    expect(isTerminalPhase(CHAT_ANSWER_PHASES.DONE)).toBe(true);
    expect(isTerminalPhase(CHAT_ANSWER_PHASES.RETRIEVAL)).toBe(false);
  });

  it('resolves answer phase from confidence', () => {
    expect(resolveAnswerPhase({ confidence: 0.9 })).toBe(CHAT_ANSWER_PHASES.DONE);
    expect(resolveAnswerPhase({ confidence: 0.4 })).toBe(CHAT_ANSWER_PHASES.DEGRADED);
    expect(resolveAnswerPhase({ lifecycle: CHAT_ANSWER_PHASES.DEGRADED })).toBe(
      CHAT_ANSWER_PHASES.DEGRADED,
    );
  });

  it('indexes pipeline phases', () => {
    expect(phaseIndex(CHAT_ANSWER_PHASES.PARSING)).toBe(0);
    expect(phaseIndex(CHAT_ANSWER_PHASES.CITATIONS)).toBe(4);
    expect(phaseIndex(CHAT_ANSWER_PHASES.ERROR)).toBeNull();
  });

  it('shows pipeline only when streaming or non-session mode', () => {
    expect(
      shouldShowAnswerPipeline(CHAT_ANSWER_PHASES.RETRIEVAL, 'streaming', true),
    ).toBe(true);
    expect(
      shouldShowAnswerPipeline(CHAT_ANSWER_PHASES.RETRIEVAL, 'session', false),
    ).toBe(false);
    expect(
      shouldShowAnswerPipeline(CHAT_ANSWER_PHASES.PARSING, 'session', false),
    ).toBe(false);
    expect(shouldShowAnswerPipeline(CHAT_ANSWER_PHASES.ERROR, 'streaming', true)).toBe(false);
  });

  it('hides retrieval trace when lifecycle pipeline is visible', () => {
    const trace = { steps: [{ id: 'a', label: 'step', status: 'active' }] };
    expect(
      shouldShowRetrievalTrace(trace, CHAT_ANSWER_PHASES.RETRIEVAL, 'streaming', true),
    ).toBe(false);
    expect(
      shouldShowRetrievalTrace(trace, CHAT_ANSWER_PHASES.RETRIEVAL, 'session', false),
    ).toBe(true);
    expect(shouldShowRetrievalTrace(null, CHAT_ANSWER_PHASES.RETRIEVAL, 'session', false)).toBe(
      false,
    );
  });
});
