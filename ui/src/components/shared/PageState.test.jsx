import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../test/renderWithProviders.jsx';
import { DegradedBanner, EmptyState, ErrorBanner } from './PageState.jsx';

describe('PageState', () => {
  it('renders empty state', () => {
    const { getByText } = renderWithProviders(
      <EmptyState title="Пусто" message="Нет данных" />,
    );
    expect(getByText('Пусто')).toBeTruthy();
    expect(getByText('Нет данных')).toBeTruthy();
  });

  it('renders error banner with retry', () => {
    const onRetry = vi.fn();
    const { getByRole, getByText } = renderWithProviders(
      <ErrorBanner message="Ошибка загрузки" onRetry={onRetry} retryLabel="Повторить" />,
    );
    getByText('Повторить').click();
    expect(onRetry).toHaveBeenCalledOnce();
    expect(getByRole('alert')).toBeTruthy();
  });

  it('renders degraded banner', () => {
    const { getByText } = renderWithProviders(
      <DegradedBanner message="Частичная деградация" />,
    );
    expect(getByText('Частичная деградация')).toBeTruthy();
  });
});
