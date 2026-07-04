import { describe, expect, it } from 'vitest';
import { getApiErrorMessage, mapApiError } from '../api/errors.js';

describe('getApiErrorMessage', () => {
  it('prefers backend message over fallback code', () => {
    expect(getApiErrorMessage({ response: { data: { message: 'Session limit reached' } } }, 'chat_create_failed'))
      .toBe('Session limit reached');
  });

  it('uses error message when backend message is absent', () => {
    expect(getApiErrorMessage(new Error('chat_create_failed'), 'request_failed'))
      .toBe('chat_create_failed');
  });

  it('returns fallback code when no message is available', () => {
    expect(getApiErrorMessage({}, 'chat_create_failed')).toBe('chat_create_failed');
  });
});

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
