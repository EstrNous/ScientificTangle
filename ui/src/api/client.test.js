import { afterEach, describe, expect, it, vi } from 'vitest';

const mockFetch = vi.fn(async (resource) => {
  if (resource === 'chat/sessions') return [];
  throw new Error(`unexpected ${resource}`);
});

vi.mock('../api/mock/index.js', () => ({
  mockFetch: (...args) => mockFetch(...args),
}));

vi.mock('./auth.js', () => ({
  ensureAuth: vi.fn(async () => 'live-token'),
  authHeaders: vi.fn((token) => ({ Authorization: `Bearer ${token}` })),
}));

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('uses mock fetch when VITE_USE_MOCK is true', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { apiGet: get } = await import('../api/client.js');
    const data = await get('/chat/sessions');
    expect(Array.isArray(data)).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith('chat/sessions', {});
  });

  it('does not use mock fetch when VITE_USE_MOCK is unset', async () => {
    vi.stubEnv('VITE_USE_MOCK', '');
    const axios = (await import('axios')).default;
    const getSpy = vi.spyOn(axios.Axios.prototype, 'request').mockResolvedValue({
      status: 200,
      data: { ok: true },
      headers: {},
      config: {},
    });
    const { apiGet: get } = await import('../api/client.js');
    const data = await get('/dictionaries');
    expect(mockFetch).not.toHaveBeenCalled();
    expect(data).toEqual({ ok: true });
    expect(getSpy).toHaveBeenCalled();
    getSpy.mockRestore();
  });

  it('attaches auth headers in live mode without explicit real flag', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const axios = (await import('axios')).default;
    const getSpy = vi.spyOn(axios.Axios.prototype, 'request').mockResolvedValue({
      status: 200,
      data: [],
      headers: {},
      config: {},
    });
    const { apiGet: get } = await import('../api/client.js');
    await get('/dictionaries');
    const config = getSpy.mock.calls[0][0];
    expect(config.headers.Authorization).toBe('Bearer live-token');
    getSpy.mockRestore();
  });

  it('apiOptions marks live requests when mock is disabled', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const { apiOptions } = await import('../api/client.js');
    expect(apiOptions()).toEqual({ real: true });
  });

  it('apiOptions stays empty in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { apiOptions } = await import('../api/client.js');
    expect(apiOptions()).toEqual({});
  });

  it('apiDelete returns null for 204 responses', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const axios = (await import('axios')).default;
    const deleteSpy = vi.spyOn(axios.Axios.prototype, 'request').mockResolvedValue({
      status: 204,
      data: undefined,
      headers: {},
      config: {},
    });
    const { apiDelete } = await import('../api/client.js');
    const data = await apiDelete('/documents/doc-1');
    expect(data).toBeNull();
    deleteSpy.mockRestore();
  });
});
