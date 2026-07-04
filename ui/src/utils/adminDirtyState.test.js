import { describe, expect, it } from 'vitest';
import {
  buildAdminBaselines,
  isPolicyDirty,
  isUserDirty,
  listDirtyPolicyIds,
  listDirtyUserIds,
} from './adminDirtyState.js';

describe('adminDirtyState', () => {
  const users = [
    { id: 'u1', role: 'admin', active: true },
    { id: 'u2', role: 'analyst', active: true },
  ];
  const policies = [
    { id: 'p1', documentId: 'doc-1', level: 'internal', exportAllowed: true, roles: ['admin'] },
  ];
  const baselines = buildAdminBaselines(users, policies);

  it('detects dirty user and policy rows', () => {
    const nextUsers = users.map((user) => (user.id === 'u2' ? { ...user, role: 'researcher' } : user));
    expect(isUserDirty(nextUsers[1], baselines.users)).toBe(true);
    expect(listDirtyUserIds(nextUsers, baselines.users)).toEqual(['u2']);

    const nextPolicies = [{ ...policies[0], level: 'confidential' }];
    expect(isPolicyDirty(nextPolicies[0], baselines.policies)).toBe(true);
    expect(listDirtyPolicyIds(nextPolicies, baselines.policies)).toEqual(['p1']);
  });
});
