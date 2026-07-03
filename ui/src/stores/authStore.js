import { create } from 'zustand';

export const ROLES = {
  DIRECTOR: 'director',
  RESEARCHER: 'researcher',
  ANALYST: 'analyst',
  ADMIN: 'admin',
  EXTERNAL_PARTNER: 'external_partner',
};

const ROLE_PAGES = {
  [ROLES.DIRECTOR]: ['chat', 'graph', 'strategic', 'lab', 'admin', 'upload', 'search'],
  [ROLES.RESEARCHER]: ['chat', 'graph', 'lab', 'upload', 'search'],
  [ROLES.ANALYST]: ['chat', 'graph', 'lab', 'upload', 'search'],
  [ROLES.ADMIN]: ['admin'],
  [ROLES.EXTERNAL_PARTNER]: ['chat'],
};

export const useAuthStore = create((set) => ({
  role: ROLES.DIRECTOR,
  accessToken: null,
  user: null,
  setRole: (role) => set({ role }),
  setAuth: ({ accessToken, user, role }) =>
    set({
      accessToken,
      user,
      role: role ?? ROLES.RESEARCHER,
    }),
  clearAuth: () => set({ accessToken: null, user: null }),
  canAccess: (pageKey, role) => (ROLE_PAGES[role] ?? []).includes(pageKey),
}));
