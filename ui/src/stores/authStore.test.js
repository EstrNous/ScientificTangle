import { describe, expect, it } from 'vitest';
import { ROLES, useAuthStore } from '../stores/authStore.js';

describe('authStore', () => {
  it('switches role', () => {
    useAuthStore.setState({ role: ROLES.ADMIN });
    expect(useAuthStore.getState().role).toBe(ROLES.ADMIN);
  });

  it('checks page access for researcher', () => {
    useAuthStore.setState({ role: ROLES.RESEARCHER });
    const { canAccess } = useAuthStore.getState();
    expect(canAccess('chat', ROLES.RESEARCHER)).toBe(true);
    expect(canAccess('admin', ROLES.RESEARCHER)).toBe(false);
  });
});
