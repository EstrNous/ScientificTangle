import { describe, expect, it, beforeEach } from 'vitest';
import { useChatAnswerStore } from './chatAnswerStore.js';
import { CHAT_ANSWER_PHASES } from '../utils/chatAnswerLifecycle.js';

describe('chatAnswerStore', () => {
  beforeEach(() => {
    useChatAnswerStore.getState().reset();
  });

  it('starts query in parsing phase', () => {
    useChatAnswerStore.getState().beginQuery('session');
    const state = useChatAnswerStore.getState();
    expect(state.phase).toBe(CHAT_ANSWER_PHASES.PARSING);
    expect(state.mode).toBe('session');
    expect(state.isActive).toBe(true);
  });

  it('advances through allowed phases', () => {
    const { beginQuery, setPhase } = useChatAnswerStore.getState();
    beginQuery('simulated');
    expect(setPhase(CHAT_ANSWER_PHASES.RETRIEVAL)).toBe(true);
    expect(useChatAnswerStore.getState().phase).toBe(CHAT_ANSWER_PHASES.RETRIEVAL);
    expect(setPhase(CHAT_ANSWER_PHASES.CITATIONS)).toBe(false);
  });

  it('completes query into terminal phase', () => {
    const { beginQuery, completeQuery } = useChatAnswerStore.getState();
    beginQuery('session');
    completeQuery(CHAT_ANSWER_PHASES.DONE);
    const state = useChatAnswerStore.getState();
    expect(state.phase).toBe(CHAT_ANSWER_PHASES.DONE);
    expect(state.isActive).toBe(false);
    expect(state.retrievalTrace).toBeNull();
  });

  it('fails query into error phase', () => {
    const { beginQuery, failQuery } = useChatAnswerStore.getState();
    beginQuery('session');
    failQuery();
    const state = useChatAnswerStore.getState();
    expect(state.phase).toBe(CHAT_ANSWER_PHASES.ERROR);
    expect(state.isActive).toBe(false);
  });

  it('stores fail reason code for error mapping', () => {
    const { beginQuery, failQuery } = useChatAnswerStore.getState();
    beginQuery('session');
    failQuery({ code: 'active_dictionary_required', message: 'seed required' });
    const state = useChatAnswerStore.getState();
    expect(state.failReason).toEqual({
      code: 'active_dictionary_required',
      message: 'seed required',
    });
  });

  it('tracks streaming draft during synthesis', () => {
    const { beginQuery, setStreamingDraft } = useChatAnswerStore.getState();
    beginQuery('streaming');
    setStreamingDraft('partial text', false);
    expect(useChatAnswerStore.getState().streamingDraft).toBe('partial text');
    expect(useChatAnswerStore.getState().streamingComplete).toBe(false);
    setStreamingDraft('partial text done', true);
    expect(useChatAnswerStore.getState().streamingComplete).toBe(true);
  });
});
