import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  mapAdminPolicy,
  mapDeleteDocumentResult,
  mapDocumentCatalogItem,
  mapExportPayload,
  mapInterest,
  mapInterestsProfile,
  mapNotification,
  mapReviewQueue,
  serializeExportRequest,
} from './mappers/productApi.js';
import { resolveUploadedDocuments } from './uploadCore.js';

describe('productApi mappers', () => {
  it('maps interests profile from snake_case payload', () => {
    const profile = mapInterestsProfile({
      raw_text: 'никель',
      interests: [{ label: 'materials', weight: 0.5, source_terms: ['никель'] }],
      extracted_entities: [{ id: 'e1' }],
      updated_at: '2026-07-04T00:00:00Z',
    });
    expect(profile.rawText).toBe('никель');
    expect(profile.interests[0]).toEqual({
      label: 'materials',
      weight: 0.5,
      sourceTerms: ['никель'],
    });
    expect(profile.extractedEntities).toEqual([{ id: 'e1' }]);
  });

  it('maps notification and review queue payloads', () => {
    const notification = mapNotification({
      id: 'n1',
      title: 'title',
      reason: 'reason',
      type: 'interest_match',
      reference_id: 'doc-1',
      reference_type: 'document',
      read: false,
      created_at: '2026-07-04T00:00:00Z',
    });
    expect(notification.referenceId).toBe('doc-1');
    expect(notification.referenceType).toBe('document');

    const queue = mapReviewQueue({
      items: [{ id: 'c1', name: 'Ni', type: 'substance', status: 'pending', confidence: 0.8 }],
      total: 1,
    });
    expect(queue.items[0].name).toBe('Ni');
    expect(queue.total).toBe(1);
  });

  it('maps notification snake_case fields and legacy is_read fallback', () => {
    const notification = mapNotification({
      id: 'n2',
      title: 'match',
      reason: '',
      message: 'legacy body',
      type: 'interest_match',
      reference_id: 'span-1',
      reference_type: 'source_span',
      is_read: true,
      match_score: 0.91,
      match_reason: 'term overlap',
      created_at: '2026-07-04T12:00:00Z',
    });
    expect(notification.reason).toBe('legacy body');
    expect(notification.read).toBe(true);
    expect(notification.matchScore).toBe(0.91);
    expect(notification.matchReason).toBe('term overlap');
  });

  it('maps review queue from contract-shaped payload with total_found', () => {
    const queue = mapReviewQueue({
      items: [
        {
          id: 'c1',
          document_id: 'doc-1',
          source_span_id: 'span-1',
          status: 'pending',
          priority: 'high',
          payload: { candidate_id: 'NiSO4', candidate_type: 'substance', confidence: 0.82 },
          created_at: '2026-07-04T07:30:00Z',
        },
      ],
      total_found: 1,
      warnings: ['queue_stale'],
    });
    expect(queue.items[0]).toMatchObject({
      name: 'NiSO4',
      type: 'substance',
      confidence: 0.82,
      documentId: 'doc-1',
      sourceSpanIds: ['span-1'],
    });
    expect(queue.total).toBe(1);
    expect(queue.warnings).toEqual(['queue_stale']);
  });

  it('maps review queue empty payload and snake_case conflicts', () => {
    const queue = mapReviewQueue({});
    expect(queue.items).toEqual([]);
    expect(queue.total).toBe(0);
    expect(queue.warnings).toEqual([]);

    const withConflicts = mapReviewQueue({
      items: [],
      total_found: 0,
      conflicts: [
        {
          id: 'conflict-1',
          claim_a: 'A',
          claim_b: 'B',
          condition_a: 'lab',
          condition_b: 'field',
          source_a: 'span-1',
          source_b: 'span-2',
        },
      ],
    });
    expect(withConflicts.conflicts[0]).toEqual({
      id: 'conflict-1',
      claimA: 'A',
      claimB: 'B',
      conditionA: 'lab',
      conditionB: 'field',
      sourceA: 'span-1',
      sourceB: 'span-2',
    });
  });

  it('resolveUploadedDocuments handles empty report and sources snake_case', () => {
    expect(resolveUploadedDocuments(null)).toEqual([]);
    expect(resolveUploadedDocuments({})).toEqual([]);
    expect(
      resolveUploadedDocuments({
        normalized_documents: [],
        sources: [
          {
            original_filename: 'pack.json',
            sha256: 'a'.repeat(64),
            content_type: 'application/json',
          },
        ],
      }),
    ).toEqual([
      {
        id: 'a'.repeat(32),
        filename: 'pack.json',
        kind: 'dictionary',
      },
    ]);
  });

  it('maps export and delete payloads', () => {
    const exportPayload = mapExportPayload({
      export_job_id: 'job-1',
      query_run_id: 'run-1',
      format: 'markdown',
      status: 'completed',
      content_type: 'text/markdown',
      content: '# report',
      file_url: 'inline://export.md',
      warnings: ['json_ld_unavailable'],
    });
    expect(exportPayload.exportJobId).toBe('job-1');
    expect(exportPayload.warnings).toContain('json_ld_unavailable');

    const deleteResult = mapDeleteDocumentResult({
      document_id: 'doc-1',
      status: 'deleted',
      tombstone_id: 't-1',
    });
    expect(deleteResult.documentId).toBe('doc-1');
    expect(deleteResult.tombstoneId).toBe('t-1');
  });

  it('serializes export request and admin policy view', () => {
    expect(serializeExportRequest({ queryRunId: 'run-1', format: 'json' })).toEqual({
      query_run_id: 'run-1',
      format: 'json',
    });
    expect(mapInterest({ label: 'x', weight: 1, source_terms: ['a'] }).sourceTerms).toEqual(['a']);
    expect(mapAdminPolicy({ id: 'p1', document_id: 'd1', level: 'internal', export_allowed: true }).exportAllowed).toBe(
      true,
    );
    expect(
      mapDocumentCatalogItem({
        document_id: 'doc-1',
        title: 'report.pdf',
        status: 'completed',
        source_spans_count: 2,
        indexed_points_count: 2,
      }).sourceSpansCount,
    ).toBe(2);
  });
});

describe('product api clients (mock mode)', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('loads and updates interests in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchInterestsProfile, updateInterestsProfile } = await import('./interests.js');
    const loaded = await fetchInterestsProfile();
    expect(loaded.rawText).toContain('Никель');
    const saved = await updateInterestsProfile({ rawText: 'Медь, флотация' });
    expect(saved.rawText).toBe('Медь, флотация');
  });

  it('loads review queue and submits decision in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchReviewQueue, submitReviewDecision } = await import('./review.js');
    const queue = await fetchReviewQueue({ status: 'pending' });
    expect(queue.items.length).toBeGreaterThan(0);
    const decision = await submitReviewDecision({
      candidateId: queue.items[0].id,
      decision: 'approved',
    });
    expect(decision.status).toBe('approved');
  });

  it('requests export and deletes document in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { requestExport } = await import('./export.js');
    const { deleteDocument } = await import('./documents.js');
    const exported = await requestExport({ queryRunId: '00000000-0000-4000-8000-000000000101', format: 'json' });
    expect(exported.format).toBe('json');
    const deleted = await deleteDocument('doc-mock-1');
    expect(deleted.status).toBe('deleted');
  });

  it('patches admin entities in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchAdminSnapshot, patchAdminUser } = await import('./admin.js');
    const admin = await fetchAdminSnapshot();
    const user = admin.users[0];
    const updated = await patchAdminUser(user.id, { role: 'researcher', active: false });
    expect(updated.role).toBe('researcher');
    expect(updated.active).toBe(false);
  });

  it('filters notifications by since in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchNotifications } = await import('./notifications.js');
    const all = await fetchNotifications();
    const filtered = await fetchNotifications({ since: '2026-07-04T00:00:00Z' });
    expect(filtered.length).toBeLessThanOrEqual(all.length);
  });

  it('loads audit events with pagination in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchAuditEvents } = await import('./audit.js');
    const page = await fetchAuditEvents({ limit: 2, offset: 0 });
    expect(page.length).toBeLessThanOrEqual(2);
  });

  it('loads eval report summary in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    const { fetchEvalReportSummary } = await import('./eval.js');
    const summary = await fetchEvalReportSummary();
    expect(summary.reportId).toBe('mock-eval-report');
    expect(summary.blockedChecks).toContain('live_eval_report');
  });
});
