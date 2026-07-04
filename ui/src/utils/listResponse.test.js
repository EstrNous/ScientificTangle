import { describe, expect, it } from 'vitest';
import { normalizeListResponse } from './listResponse.js';

describe('normalizeListResponse', () => {
  it('returns arrays as-is', () => {
    expect(normalizeListResponse([{ id: 1 }])).toEqual([{ id: 1 }]);
  });

  it('unwraps items property', () => {
    expect(normalizeListResponse({ items: [{ id: 2 }] })).toEqual([{ id: 2 }]);
  });

  it('returns empty array for invalid payloads', () => {
    expect(normalizeListResponse(null)).toEqual([]);
    expect(normalizeListResponse({})).toEqual([]);
  });
});
