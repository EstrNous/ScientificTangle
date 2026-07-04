import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  isLiveNotificationsEnabled,
  isReviewActionsEnabled,
  isReviewConsoleEnabled,
  isServerExportEnabled,
  isSourceLiveModeEnabled,
} from '../utils/uiFeatureFlags.js';

vi.mock('../api/client.js', () => ({
  useMock: false,
}));

describe('uiFeatureFlags', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('enables product flags from env', async () => {
    vi.stubEnv('VITE_SERVER_EXPORT_ENABLED', 'true');
    vi.stubEnv('VITE_LIVE_NOTIFICATIONS_ENABLED', 'true');
    vi.stubEnv('VITE_REVIEW_CONSOLE_ENABLED', 'true');
    vi.stubEnv('VITE_SOURCE_LIVE_MODE', 'true');
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isServerExportEnabled()).toBe(true);
    expect(flags.isLiveNotificationsEnabled()).toBe(true);
    expect(flags.isReviewConsoleEnabled()).toBe(true);
    expect(flags.isSourceLiveModeEnabled()).toBe(true);
  });

  it('defaults product flags to false', () => {
    expect(isServerExportEnabled()).toBe(false);
    expect(isLiveNotificationsEnabled()).toBe(false);
    expect(isReviewConsoleEnabled()).toBe(false);
    expect(isReviewActionsEnabled()).toBe(false);
    expect(isSourceLiveModeEnabled()).toBe(true);
  });

  it('enables review actions only in mock mode', async () => {
    vi.doMock('../api/client.js', () => ({ useMock: true }));
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isReviewActionsEnabled()).toBe(true);
  });
});
