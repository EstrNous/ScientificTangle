import { describe, expect, it } from 'vitest';
import {
  CHAT_ANSWER_PHASES,
  canTransitionPhase,
  isTerminalPhase,
  phaseIndex,
  resolveAnswerPhase,
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
});
