import { describe, expect, it } from 'vitest';
import { mapApiError } from '../api/errors.js';

describe('mapApiError', () => {
  it('maps http status codes to stable error codes', () => {
    expect(mapApiError({ response: { status: 403 } })).toBe('forbidden');
    expect(mapApiError({ response: { status: 404 } })).toBe('not_found');
  });

  it('prefers backend error code when present', () => {
    expect(mapApiError({ response: { status: 501, data: { code: 'document_delete_not_implemented' } } }))
      .toBe('document_delete_not_implemented');
  });
});
