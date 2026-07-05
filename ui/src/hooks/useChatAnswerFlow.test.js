import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

const sendChatMessage = vi.fn();
const tryRunQueryEventStream = vi.fn();
const uploadFiles = vi.fn();
const waitForIngestionTask = vi.fn();

vi.mock('../api/chat.js', () => ({
  sendChatMessage: (...args) => sendChatMessage(...args),
}));

vi.mock('../api/auth.js', () => ({
  ensureAuth: vi.fn(async () => 'token'),
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer token' })),
}));

vi.mock('../api/uploadCore.js', () => ({
  uploadFiles: (...args) => uploadFiles(...args),
  waitForIngestionTask: (...args) => waitForIngestionTask(...args),
}));

vi.mock('../api/queryTransport.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    isQueryStreamTransportAvailable: vi.fn(() => true),
    tryRunQueryEventStream: (...args) => tryRunQueryEventStream(...args),
  };
});

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

vi.mock('../utils/chatAnswerLifecycle.js', async () => {
  const actual = await vi.importActual('../utils/chatAnswerLifecycle.js');
  return {
    ...actual,
    isSimulatedLifecycleEnabled: vi.fn(() => false),
    resolveAnswerPhase: vi.fn(() => actual.CHAT_ANSWER_PHASES.DONE),
  };
});

vi.mock('../utils/chatFeatureFlags.js', () => ({
  isStreamingUxEnabled: vi.fn(() => true),
}));

vi.mock('../utils/uiFeatureFlags.js', () => ({
  isLiveProductionMode: vi.fn(() => true),
}));

import { useChatAnswerFlow } from './useChatAnswerFlow.js';
import { useChatAnswerStore } from '../stores/chatAnswerStore.js';
import { CHAT_ANSWER_PHASES } from '../utils/chatAnswerLifecycle.js';

describe('useChatAnswerFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatAnswerStore.getState().reset();
    tryRunQueryEventStream.mockImplementation(async (_payload, { onEvent } = {}) => {
      onEvent?.({ type: 'phase', phase: 'retrieval' });
      onEvent?.({
        type: 'done',
        payload: { id: 'run-1', answer: { answer_text: 'Стрим-ответ', confidence: 0.9 } },
      });
      return {
        ok: true,
        donePayload: { id: 'run-1', answer: { answer_text: 'Стрим-ответ', confidence: 0.9 } },
      };
    });
    sendChatMessage.mockResolvedValue({
      id: 'msg-1',
      role: 'assistant',
      content: 'Стрим-ответ',
      confidence: 0.9,
    });
  });

  it('uses stream-only path and persists chat via existing query run', async () => {
    const { result } = renderHook(() => useChatAnswerFlow());

    await act(async () => {
      await result.current.sendAnswerQuery({
        sessionId: 'session-1',
        text: 'никель',
        files: [],
      });
    });

    expect(tryRunQueryEventStream).toHaveBeenCalledTimes(1);
    expect(sendChatMessage).toHaveBeenCalledWith('session-1', 'никель', { queryRunId: 'run-1' });
    expect(useChatAnswerStore.getState().phase).toBe(CHAT_ANSWER_PHASES.DONE);
    expect(useChatAnswerStore.getState().failReason).toBeNull();
  });

  it('stores stream phase error in failReason', async () => {
    tryRunQueryEventStream.mockResolvedValueOnce({
      ok: false,
      failReason: {
        code: 'active_dictionary_required',
        message: 'seed required',
        status: null,
      },
    });

    const { result } = renderHook(() => useChatAnswerFlow());

    await act(async () => {
      await expect(
        result.current.sendAnswerQuery({
          sessionId: 'session-1',
          text: 'никель',
          files: [],
        }),
      ).rejects.toThrow('seed required');
    });

    expect(sendChatMessage).not.toHaveBeenCalled();
    expect(useChatAnswerStore.getState().phase).toBe(CHAT_ANSWER_PHASES.ERROR);
    expect(useChatAnswerStore.getState().failReason).toEqual({
      code: 'active_dictionary_required',
      message: 'seed required',
      status: null,
    });
  });
});
