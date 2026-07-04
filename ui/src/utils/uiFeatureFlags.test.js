import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  isClientExportFallbackEnabled,
  isLiveNotificationsEnabled,
  isReviewActionsEnabled,
  isReviewConsoleEnabled,
  isServerExportEnabled,
  isSourceLiveModeEnabled,
} from '../utils/uiFeatureFlags.js';

vi.mock('./runtimeMode.js', () => ({
  useMock: false,
  resolveUseMock: () => false,
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
    expect(isServerExportEnabled()).toBe(true);
    expect(isClientExportFallbackEnabled()).toBe(false);
    expect(isLiveNotificationsEnabled()).toBe(false);
    expect(isReviewConsoleEnabled()).toBe(false);
    expect(isReviewActionsEnabled()).toBe(false);
    expect(isSourceLiveModeEnabled()).toBe(true);
  });

  it('enables review actions in live mode when review console flag is on', async () => {
    vi.stubEnv('VITE_REVIEW_CONSOLE_ENABLED', 'true');
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isReviewActionsEnabled()).toBe(true);
  });

  it('enables review actions only in mock mode without review console flag', async () => {
    vi.doMock('./runtimeMode.js', () => ({
      useMock: true,
      resolveUseMock: () => true,
    }));
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isReviewActionsEnabled()).toBe(true);
  });

  it('forces source live mode in production builds even when mock is enabled', async () => {
    vi.stubEnv('PROD', 'true');
    vi.doMock('./runtimeMode.js', () => ({
      useMock: true,
      resolveUseMock: () => true,
    }));
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isSourceLiveModeEnabled()).toBe(true);
  });
});
