import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/renderWithProviders.jsx';
import ChatPage from './ChatPage.jsx';
import {
  createChatSession,
  fetchChatMessages,
  fetchChatSessions,
} from '../api/chat.js';
import { ensureAuth } from '../api/auth.js';

const { mockReset } = vi.hoisted(() => ({
  mockReset: vi.fn(),
}));

vi.mock('../api/auth.js', () => ({
  ensureAuth: vi.fn(() => Promise.resolve()),
}));

vi.mock('../api/chat.js', () => ({
  fetchChatSessions: vi.fn(),
  fetchChatMessages: vi.fn(),
  createChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  sendChatMessage: vi.fn(),
}));


vi.mock('../hooks/useChatAnswerFlow.js', () => ({
  useChatAnswerFlow: () => ({
    phase: 'idle',
    retrievalTrace: null,
    streamingDraft: '',
    streamingComplete: false,
    mode: 'session',
    isActive: false,
    streamingUxEnabled: false,
    sendAnswerQuery: vi.fn(),
    reset: mockReset,
  }),
}));

describe('ChatPage new chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReset.mockClear();
    fetchChatSessions.mockResolvedValue([]);
    fetchChatMessages.mockResolvedValue([]);
  });

  it('creates a session when new chat is clicked', async () => {
    const created = {
      id: 'session-new',
      title: 'Новый запрос',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };
    createChatSession.mockResolvedValue(created);

    renderWithProviders(<ChatPage />);
    await waitFor(() => {
      expect(ensureAuth).toHaveBeenCalled();
    });

    const user = userEvent.setup();
    await user.click(screen.getAllByRole('button', { name: 'Новый чат' })[0]);

    await waitFor(() => {
      expect(createChatSession).toHaveBeenCalledTimes(1);
      expect(createChatSession).toHaveBeenCalledWith('Новый запрос');
      expect(mockReset).toHaveBeenCalledTimes(1);
    });
  });

  it('resets answer flow when switching sessions', async () => {
    const sessions = [
      {
        id: 'session-a',
        title: 'Запрос A',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 'session-b',
        title: 'Запрос B',
        created_at: '2026-01-02T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      },
    ];
    fetchChatSessions.mockResolvedValue(sessions);
    fetchChatMessages.mockResolvedValue([]);

    renderWithProviders(<ChatPage />);
    await waitFor(() => {
      expect(fetchChatSessions).toHaveBeenCalled();
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Запрос B' }));

    expect(mockReset).toHaveBeenCalledTimes(1);
  });

  it('does not create a duplicate when current draft is already empty', async () => {
    const draft = {
      id: 'session-draft',
      title: 'Новый запрос',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };
    createChatSession.mockResolvedValue(draft);
    fetchChatSessions.mockResolvedValue([draft]);
    fetchChatMessages.mockResolvedValue([]);

    renderWithProviders(<ChatPage />);
    await waitFor(() => {
      expect(fetchChatSessions).toHaveBeenCalled();
    });

    const user = userEvent.setup();
    await user.click(screen.getAllByRole('button', { name: 'Новый чат' })[0]);

    await waitFor(() => {
      expect(createChatSession).not.toHaveBeenCalled();
    });
  });
});
