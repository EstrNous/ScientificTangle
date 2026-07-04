import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  mapAdminPolicy,
  mapDeleteDocumentResult,
  mapExportPayload,
  mapInterest,
  mapInterestsProfile,
  mapNotification,
  mapReviewQueue,
  serializeExportRequest,
} from './mappers/productApi.js';

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
});
