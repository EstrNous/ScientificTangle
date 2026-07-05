import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { sendChatMessage } from '../api/chat.js';
import { ensureAuth, authHeaders } from '../api/auth.js';
import { uploadFiles, waitForIngestionTask } from '../api/uploadCore.js';
import {
  isQueryStreamTransportAvailable,
  mapQueryRunToMessage,
  resolveQueryRunIdFromDonePayload,
  shouldFallbackToChatQuery,
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

function resolveQueryFailureReason(error) {
  const data = error?.response?.data;
  return {
    code: data?.code ?? null,
    message: data?.message ?? error?.message ?? null,
    status: error?.response?.status ?? null,
  };
}

function reportQueryFailure(error, failQuery) {
  if (error?.failReason) {
    failQuery(error.failReason);
    return;
  }
  failQuery(resolveQueryFailureReason(error));
}

function createQueryEventHandlers({
  setPhase,
  setRetrievalTrace,
  setStreamingDraft,
  onStreamError,
}) {
  return {
    onEvent: (event) => {
      applyQueryEvent(
        {
          onPhaseChange: setPhase,
          onRetrievalStep: setRetrievalTrace,
          onStreamingDraft: (draft, complete) => setStreamingDraft(draft, complete),
          onStreamError,
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
  const failReason = useChatAnswerStore((state) => state.failReason);
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
          reportQueryFailure(error, failQuery);
          throw error;
        }
      }

      const queryMode = liveProduction && streamingUxEnabled ? 'live' : 'session';
      beginQuery(queryMode);

      try {
        if (files.length > 0) {
          const task = await uploadFiles(files);
          if (task?.id) {
            await waitForIngestionTask(task.id);
          }
        }

        let queryText = text.trim();
        if (!queryText && files.length > 0) {
          queryText = t('chat.attachmentQuery');
        }

        if (liveProduction && streamingUxEnabled && isQueryStreamTransportAvailable()) {
          let streamError = null;
          const handlers = createQueryEventHandlers({
            setPhase,
            setRetrievalTrace,
            setStreamingDraft,
            onStreamError: (reason) => {
              streamError = reason;
            },
          });
          const token = await ensureAuth();
          const streamResult = await tryRunQueryEventStream(
            { question: queryText, authorization: authHeaders(token).Authorization },
            { onEvent: handlers.onEvent },
          );
          const streamFailReason = streamResult?.failReason ?? streamError;
          const donePayload = streamResult?.donePayload;
          if (streamResult?.ok && donePayload) {
            const queryRunId = resolveQueryRunIdFromDonePayload(donePayload);
            const reply = queryRunId
              ? await sendChatMessage(sessionId, queryText, { queryRunId })
              : mapQueryRunToMessage(donePayload, t);
            const trace = mapRetrievalTraceFromResponse(reply, t);
            if (trace) setRetrievalTrace(trace);
            const terminalPhase = resolveAnswerPhase(reply);
            completeQuery(terminalPhase);
            return { ...reply, lifecycle: terminalPhase };
          }
          if (!shouldFallbackToChatQuery(streamResult)) {
            const missingReason = streamFailReason ?? {
              code: 'query_stream_failed',
              message: 'Stream finished without answer',
              status: null,
            };
            failQuery(missingReason);
            throw Object.assign(new Error(missingReason.message ?? 'query_stream_failed'), {
              failReason: missingReason,
            });
          }
        }

        const reply = await sendChatMessage(sessionId, queryText);
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
        reportQueryFailure(error, failQuery);
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
    failReason,
    simulationEnabled,
    streamingUxEnabled,
    liveProduction,
    sendAnswerQuery,
    reset,
  };
}
