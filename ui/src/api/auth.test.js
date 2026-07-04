import { afterEach, describe, expect, it, vi } from 'vitest';

const authHttp = {
  post: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

vi.mock('axios', () => ({
  default: {
    create: () => authHttp,
  },
}));

describe('ensureAuth', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    authHttp.post.mockReset();
    authHttp.get.mockReset();
  });

  it('restores live session via refresh when access token is missing', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.resetModules();
    authHttp.post.mockResolvedValueOnce({
      data: {
        access_token: 'live-access-token',
        user: { id: '1', username: 'admin', email: 'admin@example.com', role: 'admin', is_active: true },
      },
    });
    authHttp.get.mockResolvedValueOnce({
      data: { id: '1', username: 'admin', email: 'admin@example.com', role: 'admin', is_active: true },
    });
    const { ensureAuth } = await import('./auth.js');
    const { useAuthStore } = await import('../stores/authStore.js');
    useAuthStore.getState().clearAuth();
    const token = await ensureAuth();
    expect(token).toBe('live-access-token');
    expect(authHttp.post).toHaveBeenCalledWith('/api/auth/refresh');
    expect(useAuthStore.getState().user?.username).toBe('admin');
  });

  it('throws when live session cannot be restored', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.resetModules();
    authHttp.post.mockRejectedValueOnce(new Error('unauthorized'));
    const { ensureAuth } = await import('./auth.js');
    const { useAuthStore } = await import('../stores/authStore.js');
    useAuthStore.getState().clearAuth();
    await expect(ensureAuth()).rejects.toThrow('unauthorized');
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
