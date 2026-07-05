import { describe, expect, it, vi } from 'vitest';
import {
  buildAuditCsv,
  downloadAuditCsv,
} from './auditCsv.js';
import {
  downloadExportPayload,
  isExportProcessing,
  isRemoteExportUrl,
} from './exportDelivery.js';
import { resolveAuditEventTarget } from './auditNavigation.js';

describe('exportDelivery', () => {
  it('detects remote export urls', () => {
    expect(isRemoteExportUrl('https://example.com/file.md')).toBe(true);
    expect(isRemoteExportUrl('inline://export.md')).toBe(false);
  });

  it('detects processing export statuses', () => {
    expect(isExportProcessing('processing')).toBe(true);
    expect(isExportProcessing('completed')).toBe(false);
  });

  it('downloads inline export content', () => {
    const click = vi.fn();
    const createObjectURL = vi.fn(() => 'blob:1');
    const revokeObjectURL = vi.fn();
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    vi.stubGlobal(
      'document',
      {
        createElement: () => ({ click, download: '' }),
      },
    );

    downloadExportPayload({
      format: 'markdown',
      content: '# report',
      contentType: 'text/markdown',
      fileUrl: '',
    });

    expect(click).toHaveBeenCalled();
    expect(createObjectURL).toHaveBeenCalled();
  });
});

describe('auditNavigation', () => {
  it('resolves query run drill-down', () => {
    expect(
      resolveAuditEventTarget({
        details: { query_run_id: 'run-1' },
      }),
    ).toEqual({
      kind: 'navigate',
      path: '/chat',
      state: { queryRunId: 'run-1' },
    });
  });

  it('resolves source drill-down', () => {
    expect(
      resolveAuditEventTarget({
        source_span_id: 'span-1',
      }),
    ).toEqual({
      kind: 'source',
      ref: 'span-1',
    });
  });

  it('resolves ingestion task drill-down with ingestionTaskId state', () => {
    expect(
      resolveAuditEventTarget({
        resource_type: 'ingestion_task',
        resource_id: 'task-1',
      }),
    ).toEqual({
      kind: 'navigate',
      path: '/upload',
      state: { ingestionTaskId: 'task-1' },
    });
  });

  it('resolves document drill-down with documentId state', () => {
    expect(
      resolveAuditEventTarget({
        details: { document_id: 'doc-1' },
      }),
    ).toEqual({
      kind: 'navigate',
      path: '/upload',
      state: { documentId: 'doc-1' },
    });
  });

  it('resolves review item drill-down with candidateId state', () => {
    expect(
      resolveAuditEventTarget({
        resource_type: 'review_item',
        resource_id: 'c-1',
      }),
    ).toEqual({
      kind: 'navigate',
      path: '/review',
      state: { candidateId: 'c-1' },
    });
  });
});

describe('auditCsv', () => {
  it('builds csv with escaped values', () => {
    const csv = buildAuditCsv([
      {
        id: '1',
        timestamp: '2026-07-04',
        user: 'a',
        role: 'admin',
        action: 'query_created',
        object: 'obj, "quoted"',
        resource_type: '',
        resource_id: '',
      },
    ]);
    expect(csv).toContain('"obj, ""quoted"""');
  });

  it('triggers csv download', () => {
    const click = vi.fn();
    vi.stubGlobal('URL', {
      createObjectURL: () => 'blob:csv',
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal(
      'document',
      {
        createElement: () => ({ click, download: '' }),
      },
    );
    downloadAuditCsv([{ id: '1' }], 'audit.csv');
    expect(click).toHaveBeenCalled();
  });
});
