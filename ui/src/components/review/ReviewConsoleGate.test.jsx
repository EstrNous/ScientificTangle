import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

describe('ReviewConsoleGate', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('renders children when feature flag is enabled', async () => {
    vi.stubEnv('VITE_REVIEW_CONSOLE_ENABLED', 'true');
    vi.resetModules();
    const { default: ReviewConsoleGate } = await import('./ReviewConsoleGate.jsx');
    render(
      <MemoryRouter initialEntries={['/review']}>
        <Routes>
          <Route
            path="/review"
            element={
              <ReviewConsoleGate>
                <div>review-console</div>
              </ReviewConsoleGate>
            }
          />
          <Route path="/chat" element={<div>chat-page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('review-console')).toBeInTheDocument();
  });

  it('redirects to chat when feature flag is disabled', async () => {
    vi.stubEnv('VITE_REVIEW_CONSOLE_ENABLED', 'false');
    vi.resetModules();
    const { default: ReviewConsoleGate } = await import('./ReviewConsoleGate.jsx');
    render(
      <MemoryRouter initialEntries={['/review']}>
        <Routes>
          <Route
            path="/review"
            element={
              <ReviewConsoleGate>
                <div>review-console</div>
              </ReviewConsoleGate>
            }
          />
          <Route path="/chat" element={<div>chat-page</div>} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('chat-page')).toBeInTheDocument();
    });
  });
});
