import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import ChatWindow from './ChatWindow.jsx';
import { CHAT_ANSWER_PHASES } from '../../utils/chatAnswerLifecycle.js';

describe('ChatWindow', () => {
  it('shows empty state when there are no messages', () => {
    const { getByText } = renderWithProviders(<ChatWindow messages={[]} />);
    expect(getByText('Задайте вопрос, чтобы начать диалог')).toBeTruthy();
  });

  it('renders error lifecycle panel', () => {
    const { getByText } = renderWithProviders(
      <ChatWindow
        messages={[]}
        answerPhase={CHAT_ANSWER_PHASES.ERROR}
        answerMode="session"
      />,
    );
    expect(getByText('Не удалось завершить подготовку ответа')).toBeTruthy();
  });

  it('renders degraded lifecycle panel', () => {
    const { getByText } = renderWithProviders(
      <ChatWindow
        messages={[]}
        answerPhase={CHAT_ANSWER_PHASES.DEGRADED}
        answerMode="session"
      />,
    );
    expect(getByText('Ответ сформирован с ограниченной уверенностью')).toBeTruthy();
  });

  it('hides retrieval trace when lifecycle pipeline is active', () => {
    const trace = {
      steps: [{ id: 'search', label: 'Поиск', status: 'active' }],
    };
    const { queryByText, getByText } = renderWithProviders(
      <ChatWindow
        messages={[]}
        retrievalTrace={trace}
        answerPhase={CHAT_ANSWER_PHASES.RETRIEVAL}
        answerMode="streaming"
        streamingUxEnabled
      />,
    );
    expect(getByText('Подготовка ответа')).toBeTruthy();
    expect(queryByText('Поиск и обработка')).toBeNull();
  });

  it('shows retrieval trace in session mode without streaming pipeline', () => {
    const trace = {
      steps: [{ id: 'search', label: 'Поиск', status: 'active' }],
    };
    const { getByText } = renderWithProviders(
      <ChatWindow
        messages={[]}
        retrievalTrace={trace}
        answerPhase={CHAT_ANSWER_PHASES.RETRIEVAL}
        answerMode="session"
        streamingUxEnabled={false}
      />,
    );
    expect(getByText('Поиск и обработка')).toBeTruthy();
  });
});
