import { describe, expect, it, vi, beforeEach } from 'vitest';

describe('documents api', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv('VITE_USE_MOCK', 'true');
  });

  it('loads single document in mock mode', async () => {
    const { fetchDocument } = await import('./documents.js');
    const item = await fetchDocument('doc-1');
    expect(item.documentId).toBe('doc-1');
    expect(item.title).toBe('doc-1');
  });
});
