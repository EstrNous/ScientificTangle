import { describe, expect, it, vi } from 'vitest';
import { resolveNotificationTarget, notificationTitleKey } from './notificationNavigation.js';

describe('notificationNavigation', () => {
  it('opens source for document and source_span references', () => {
    expect(resolveNotificationTarget({ referenceType: 'document', referenceId: 'doc-1' })).toEqual({
      kind: 'source',
      ref: 'doc-1',
    });
    expect(resolveNotificationTarget({ referenceType: 'source_span', referenceId: 'span-1' })).toEqual({
      kind: 'source',
      ref: 'span-1',
    });
  });

  it('navigates to review and chat targets', () => {
    expect(resolveNotificationTarget({ referenceType: 'review_item', referenceId: 'c-1' })).toEqual({
      kind: 'navigate',
      path: '/review',
      state: { candidateId: 'c-1' },
    });
    expect(resolveNotificationTarget({ referenceType: 'query_run', referenceId: 'run-1' })).toEqual({
      kind: 'navigate',
      path: '/chat',
      state: { queryRunId: 'run-1' },
    });
  });

  it('returns title key by notification type', () => {
    expect(notificationTitleKey('interest_match')).toBe('notifications.types.interest_match');
    expect(notificationTitleKey(null)).toBeNull();
  });
});

describe('interestsWorkflow', () => {
  it('uses local storage in mock mode', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    vi.resetModules();
    const { saveInterestsProfile, loadInterestsProfile } = await import('./interestsWorkflow.js');
    await saveInterestsProfile('user-1', 'никель, флотация');
    const profile = await loadInterestsProfile('user-1');
    expect(profile.rawText).toContain('никель');
    expect(profile.interests.length).toBeGreaterThan(0);
  });
});
