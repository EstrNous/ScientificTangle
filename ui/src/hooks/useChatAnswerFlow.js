import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { sendChatMessage } from '../api/chat.js';
import { useChatAnswerStore } from '../stores/chatAnswerStore.js';
import {
  CHAT_ANSWER_PHASES,
  isSimulatedLifecycleEnabled,
  resolveAnswerPhase,
} from '../utils/chatAnswerLifecycle.js';
import { runSimulatedAnswerLifecycle } from '../utils/runSimulatedAnswerLifecycle.js';

export function useChatAnswerFlow() {
  const { t } = useTranslation();
  const phase = useChatAnswerStore((state) => state.phase);
  const retrievalTrace = useChatAnswerStore((state) => state.retrievalTrace);
  const mode = useChatAnswerStore((state) => state.mode);
  const isActive = useChatAnswerStore((state) => state.isActive);
  const beginQuery = useChatAnswerStore((state) => state.beginQuery);
  const setPhase = useChatAnswerStore((state) => state.setPhase);
  const setRetrievalTrace = useChatAnswerStore((state) => state.setRetrievalTrace);
  const completeQuery = useChatAnswerStore((state) => state.completeQuery);
  const failQuery = useChatAnswerStore((state) => state.failQuery);
  const reset = useChatAnswerStore((state) => state.reset);

  const simulationEnabled = isSimulatedLifecycleEnabled();

  const sendAnswerQuery = useCallback(
    async ({ sessionId, text, files = [] }) => {
      if (simulationEnabled) {
        beginQuery('simulated');
        try {
          const reply = await runSimulatedAnswerLifecycle(
            { text, files },
            {
              t,
              onPhaseChange: setPhase,
              onRetrievalStep: setRetrievalTrace,
            },
          );
          completeQuery(reply.lifecycle ?? CHAT_ANSWER_PHASES.DONE);
          return reply;
        } catch (error) {
          failQuery();
          throw error;
        }
      }

      beginQuery('session');
      try {
        const reply = await sendChatMessage(sessionId, text);
        const terminalPhase = resolveAnswerPhase(reply);
        completeQuery(terminalPhase);
        return { ...reply, lifecycle: terminalPhase };
      } catch (error) {
        failQuery();
        throw error;
      }
    },
    [
      beginQuery,
      completeQuery,
      failQuery,
      setPhase,
      setRetrievalTrace,
      simulationEnabled,
      t,
    ],
  );

  return {
    phase,
    retrievalTrace,
    mode,
    isActive,
    simulationEnabled,
    sendAnswerQuery,
    reset,
  };
}
