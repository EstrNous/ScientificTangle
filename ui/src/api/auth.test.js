import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('axios', () => ({
  default: {
    create: () => ({
      post: vi.fn(),
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    }),
  },
}));

describe('ensureAuth', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('throws auth_required in live mode without token', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.resetModules();
    const { ensureAuth } = await import('./auth.js');
    const { useAuthStore } = await import('../stores/authStore.js');
    useAuthStore.getState().clearAuth();
    await expect(ensureAuth()).rejects.toThrow('auth_required');
  });

  it('applies mock auth when mock mode and credentials are set', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    vi.stubEnv('VITE_AUTH_USERNAME', 'researcher');
    vi.stubEnv('VITE_AUTH_PASSWORD', 'secret');
    vi.resetModules();
    const { ensureAuth } = await import('./auth.js');
    const { useAuthStore } = await import('../stores/authStore.js');
    useAuthStore.getState().clearAuth();
    const token = await ensureAuth();
    expect(token).toBe('mock-access-token');
    expect(useAuthStore.getState().user?.username).toBe('researcher');
  });
});
