import { create } from 'zustand';
import {
  CHAT_ANSWER_PHASES,
  canTransitionPhase,
  isTerminalPhase,
} from '../utils/chatAnswerLifecycle.js';

const initialState = {
  phase: CHAT_ANSWER_PHASES.IDLE,
  retrievalTrace: null,
  mode: 'session',
  isActive: false,
};

export const useChatAnswerStore = create((set, get) => ({
  ...initialState,
  setMode: (mode) => set({ mode }),
  setPhase: (nextPhase) => {
    const current = get().phase;
    if (!canTransitionPhase(current, nextPhase)) {
      return false;
    }
    set({ phase: nextPhase, isActive: !isTerminalPhase(nextPhase) });
    return true;
  },
  setRetrievalTrace: (retrievalTrace) => set({ retrievalTrace }),
  beginQuery: (mode = 'session') =>
    set({
      mode,
      phase: CHAT_ANSWER_PHASES.PARSING,
      retrievalTrace: null,
      isActive: true,
    }),
  completeQuery: (terminalPhase = CHAT_ANSWER_PHASES.DONE) =>
    set({
      phase: terminalPhase,
      retrievalTrace: null,
      isActive: false,
    }),
  failQuery: () =>
    set({
      phase: CHAT_ANSWER_PHASES.ERROR,
      retrievalTrace: null,
      isActive: false,
    }),
  reset: () => set({ ...initialState }),
}));
