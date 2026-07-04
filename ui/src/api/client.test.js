import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api/mock/index.js', () => ({
  mockFetch: vi.fn(async (resource) => {
    if (resource === 'chat/sessions') return [];
    throw new Error(`unexpected ${resource}`);
  }),
}));

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses mock fetch when VITE_USE_MOCK is not false', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    vi.resetModules();
    const { apiGet: get } = await import('../api/client.js');
    const data = await get('/chat/sessions');
    expect(Array.isArray(data)).toBe(true);
  });
});
