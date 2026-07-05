import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import ChatInput from './ChatInput.jsx';

describe('ChatInput', () => {
  it('renders input', () => {
    const onSend = vi.fn();
    const { getByPlaceholderText } = renderWithProviders(<ChatInput onSend={onSend} />);
    expect(getByPlaceholderText('Задайте вопрос…')).toBeTruthy();
  });
});
