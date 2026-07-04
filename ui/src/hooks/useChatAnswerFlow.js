import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { sendChatMessage } from '../api/chat.js';
import { ensureAuth, authHeaders } from '../api/auth.js';
import {
  isQueryStreamTransportAvailable,
  tryRunQueryEventStream,
} from '../api/queryTransport.js';
import { useChatAnswerStore } from '../stores/chatAnswerStore.js';
import {
  CHAT_ANSWER_PHASES,
  isSimulatedLifecycleEnabled,
  resolveAnswerPhase,
} from '../utils/chatAnswerLifecycle.js';
import { isStreamingUxEnabled } from '../utils/chatFeatureFlags.js';
import { applyQueryEvent, mapRetrievalTraceFromResponse } from '../utils/queryEventAdapter.js';
import { revealMarkdownText } from '../utils/growingMarkdown.js';
import { isLiveProductionMode } from '../utils/uiFeatureFlags.js';
import { runSimulatedAnswerLifecycle } from '../utils/runSimulatedAnswerLifecycle.js';
import { runStreamingAnswerLifecycle } from '../utils/runStreamingAnswerLifecycle.js';

function createQueryEventHandlers({ setPhase, setRetrievalTrace, setStreamingDraft }) {
  return {
    onEvent: (event) => {
      applyQueryEvent(
        {
          onPhaseChange: setPhase,
          onRetrievalStep: setRetrievalTrace,
          onStreamingDraft: (draft, complete) => setStreamingDraft(draft, complete),
        },
        event,
      );
    },
  };
}

export function useChatAnswerFlow() {
  const { t } = useTranslation();
  const phase = useChatAnswerStore((state) => state.phase);
  const retrievalTrace = useChatAnswerStore((state) => state.retrievalTrace);
  const streamingDraft = useChatAnswerStore((state) => state.streamingDraft);
  const streamingComplete = useChatAnswerStore((state) => state.streamingComplete);
  const mode = useChatAnswerStore((state) => state.mode);
  const isActive = useChatAnswerStore((state) => state.isActive);
  const beginQuery = useChatAnswerStore((state) => state.beginQuery);
  const setPhase = useChatAnswerStore((state) => state.setPhase);
  const setRetrievalTrace = useChatAnswerStore((state) => state.setRetrievalTrace);
  const setStreamingDraft = useChatAnswerStore((state) => state.setStreamingDraft);
  const completeQuery = useChatAnswerStore((state) => state.completeQuery);
  const failQuery = useChatAnswerStore((state) => state.failQuery);
  const reset = useChatAnswerStore((state) => state.reset);

  const simulationEnabled = isSimulatedLifecycleEnabled();
  const streamingUxEnabled = isStreamingUxEnabled();
  const liveProduction = isLiveProductionMode();

  const sendAnswerQuery = useCallback(
    async ({ sessionId, text, files = [] }) => {
      if (simulationEnabled) {
        beginQuery(streamingUxEnabled ? 'streaming' : 'simulated');
        const lifecycleRunner = streamingUxEnabled
          ? runStreamingAnswerLifecycle
          : runSimulatedAnswerLifecycle;
        try {
          const reply = await lifecycleRunner(
            { text, files },
            {
              t,
              onPhaseChange: setPhase,
              onRetrievalStep: setRetrievalTrace,
              onStreamingDraft: (draft, complete) => setStreamingDraft(draft, complete),
              phaseDelayMs: streamingUxEnabled ? 200 : 350,
              stepDelayMs: streamingUxEnabled ? 300 : 650,
              chunkDelayMs: 30,
            },
          );
          completeQuery(reply.lifecycle ?? CHAT_ANSWER_PHASES.DONE);
          return reply;
        } catch (error) {
          failQuery();
          throw error;
        }
      }

      const queryMode = liveProduction && streamingUxEnabled ? 'live' : 'session';
      beginQuery(queryMode);

      if (liveProduction && streamingUxEnabled && isQueryStreamTransportAvailable()) {
        const handlers = createQueryEventHandlers({
          setPhase,
          setRetrievalTrace,
          setStreamingDraft,
        });
        try {
          const token = await ensureAuth();
          const controller = new AbortController();
          const streamPromise = tryRunQueryEventStream(
            { question: text, authorization: authHeaders(token).Authorization },
            { onEvent: handlers.onEvent, signal: controller.signal },
          );
          const reply = await sendChatMessage(sessionId, text);
          controller.abort();
          await streamPromise;
          const trace = mapRetrievalTraceFromResponse(reply, t);
          if (trace) setRetrievalTrace(trace);
          const terminalPhase = resolveAnswerPhase(reply);
          completeQuery(terminalPhase);
          return { ...reply, lifecycle: terminalPhase };
        } catch (error) {
          failQuery();
          throw error;
        }
      }

      try {
        const reply = await sendChatMessage(sessionId, text);
        if (streamingUxEnabled) {
          const trace = mapRetrievalTraceFromResponse(reply, t);
          if (trace) setRetrievalTrace(trace);
          if (reply.content) {
            setPhase(CHAT_ANSWER_PHASES.SYNTHESIS);
            await revealMarkdownText(reply.content, {
              onReveal: (partial) => setStreamingDraft(partial, false),
              chunkDelayMs: 15,
            });
            setStreamingDraft(reply.content, true);
            setPhase(CHAT_ANSWER_PHASES.CITATIONS);
          }
        }
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
      liveProduction,
      setPhase,
      setRetrievalTrace,
      setStreamingDraft,
      simulationEnabled,
      streamingUxEnabled,
      t,
    ],
  );

  return {
    phase,
    retrievalTrace,
    streamingDraft,
    streamingComplete,
    mode,
    isActive,
    simulationEnabled,
    streamingUxEnabled,
    liveProduction,
    sendAnswerQuery,
    reset,
  };
}
