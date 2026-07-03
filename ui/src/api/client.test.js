import { describe, expect, it, vi } from 'vitest';
import { apiGet } from '../api/client.js';

vi.mock('../api/mock/index.js', () => ({
  mockFetch: vi.fn(async (resource) => {
    if (resource === 'chat/sessions') return [];
    throw new Error(`unexpected ${resource}`);
  }),
}));

describe('api client', () => {
  it('uses mock fetch when VITE_USE_MOCK is not false', async () => {
    const data = await apiGet('/chat/sessions');
    expect(Array.isArray(data)).toBe(true);
  });
});
