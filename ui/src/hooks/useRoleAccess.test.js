import { describe, expect, it } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useRoleAccess } from '../hooks/useRoleAccess.js';
import { ROLES, useAuthStore } from '../stores/authStore.js';

describe('useRoleAccess', () => {
  it('returns access for current role', () => {
    useAuthStore.setState({ role: ROLES.EXTERNAL_PARTNER });
    const { result } = renderHook(() => useRoleAccess());
    expect(result.current.canAccess('chat')).toBe(true);
    expect(result.current.canAccess('admin')).toBe(false);
  });
});
