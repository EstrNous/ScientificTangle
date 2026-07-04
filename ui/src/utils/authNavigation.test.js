import { describe, expect, it } from 'vitest';
import { ROLES, useAuthStore } from '../stores/authStore.js';
import { getDefaultRouteForRole, resolvePostAuthPath } from './authNavigation.js';

describe('authNavigation', () => {
  it('routes admin to admin console', () => {
    expect(getDefaultRouteForRole(ROLES.ADMIN)).toBe('/admin');
  });

  it('routes external partner to chat', () => {
    expect(getDefaultRouteForRole(ROLES.EXTERNAL_PARTNER)).toBe('/chat');
  });

  it('falls back to chat for unknown role', () => {
    expect(getDefaultRouteForRole(null)).toBe('/chat');
  });

  it('redirects admin away from chat return url', () => {
    useAuthStore.setState({ role: ROLES.ADMIN });
    expect(resolvePostAuthPath(ROLES.ADMIN, '/chat')).toBe('/admin');
  });

  it('keeps allowed return url for researcher', () => {
    expect(resolvePostAuthPath(ROLES.RESEARCHER, '/profile')).toBe('/profile');
  });
});
