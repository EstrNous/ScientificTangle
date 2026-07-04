import { create } from 'zustand';

export const ROLES = {
  DIRECTOR: 'director',
  RESEARCHER: 'researcher',
  ANALYST: 'analyst',
  ADMIN: 'admin',
  EXTERNAL_PARTNER: 'external_partner',
};

const ROLE_PAGES = {
  [ROLES.DIRECTOR]: ['chat', 'graph', 'strategic', 'lab', 'admin', 'upload', 'search', 'profile', 'review'],
  [ROLES.RESEARCHER]: ['chat', 'graph', 'lab', 'upload', 'search', 'profile', 'review'],
  [ROLES.ANALYST]: ['chat', 'graph', 'lab', 'upload', 'search', 'profile', 'review'],
  [ROLES.ADMIN]: ['admin', 'upload', 'profile', 'review'],
  [ROLES.EXTERNAL_PARTNER]: ['chat', 'profile'],
};

export const useAuthStore = create((set) => ({
  role: null,
  accessToken: null,
  user: null,
  setRole: (role) => set({ role }),
  setAuth: ({ accessToken, user, role }) =>
    set({
      accessToken,
      user,
      role: role ?? null,
    }),
  clearAuth: () => set({ accessToken: null, user: null, role: null }),
  canAccess: (pageKey, role) => (role ? (ROLE_PAGES[role] ?? []).includes(pageKey) : false),
}));
