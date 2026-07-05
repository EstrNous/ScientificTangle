import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('./auth.js', () => ({
  ensureAuth: vi.fn(async () => 'token'),
}));

import {
  canDeleteAuditDocument,
  resolveDocumentIdFromAuditEvent,
  resolveUploadedDocuments,
  uploadFiles,
  waitForIngestionTask,
} from './uploadCore.js';

describe('uploadCore helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('resolves document id from audit details', () => {
    expect(resolveDocumentIdFromAuditEvent({ details: { document_id: 'doc-1' } })).toBe('doc-1');
    expect(
      resolveDocumentIdFromAuditEvent({ details: { document_ids: ['doc-a', 'doc-b'] } }),
    ).toBe('doc-a');
    expect(resolveDocumentIdFromAuditEvent({ details: {} })).toBeNull();
  });

  it('allows delete for ingestion upload actions with document id', () => {
    expect(
      canDeleteAuditDocument({
        action: 'document_uploaded',
        details: { document_id: 'doc-1' },
      }),
    ).toBe(true);
    expect(
      canDeleteAuditDocument({
        action: 'query_submitted',
        details: { document_id: 'doc-1' },
      }),
    ).toBe(false);
  });

  it('maps normalized documents from ingestion report', () => {
    const items = resolveUploadedDocuments({
      normalized_documents: [
        { id: 'doc-1', title: 'sample.pdf', metadata: { upload_kind: 'document' }, source_type: 'pdf' },
        { id: 'dict-1', title: 'dictionary.json', metadata: { upload_kind: 'dictionary' }, source_type: 'json' },
      ],
    });
    expect(items).toEqual([
      { id: 'doc-1', filename: 'sample.pdf', kind: 'document' },
      { id: 'dict-1', filename: 'dictionary.json', kind: 'dictionary' },
    ]);
  });

  it('waits until ingestion task completes', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'pending' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'completed', id: 'task-1' }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const result = await waitForIngestionTask('task-1', { intervalMs: 1, timeoutMs: 1000 });
    expect(result.status).toBe('completed');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('throws when upload response is not ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 413 }));
    await expect(uploadFiles([new File(['x'], 'sample.txt')])).rejects.toThrow('upload_failed');
  });

  it('throws when task polling returns non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }));
    await expect(waitForIngestionTask('task-1', { intervalMs: 1, timeoutMs: 1000 })).rejects.toThrow(
      'upload_failed',
    );
  });

  it('throws when task polling reports failed status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'failed' }),
    }));
    await expect(waitForIngestionTask('task-1', { intervalMs: 1, timeoutMs: 1000 })).rejects.toThrow(
      'upload_failed',
    );
  });
});
