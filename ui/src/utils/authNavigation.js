import { ROLES, useAuthStore } from '../stores/authStore.js';

const ROLE_LANDING = {
  [ROLES.ADMIN]: '/admin',
  [ROLES.DIRECTOR]: '/chat',
  [ROLES.RESEARCHER]: '/chat',
  [ROLES.ANALYST]: '/chat',
  [ROLES.EXTERNAL_PARTNER]: '/chat',
};

const PATH_PREFIX_KEYS = [
  ['/strategic', 'strategic'],
  ['/lab', 'lab'],
  ['/admin', 'admin'],
  ['/review', 'review'],
  ['/profile', 'profile'],
];

const PATH_KEYS = {
  '/chat': 'chat',
  '/graph': 'graph',
  '/upload': 'upload',
  '/search': 'search',
};

function resolvePageKey(pathname) {
  const prefix = PATH_PREFIX_KEYS.find(([path]) => pathname.startsWith(path));
  if (prefix) return prefix[1];
  return PATH_KEYS[pathname] ?? null;
}

export function getDefaultRouteForRole(role) {
  return ROLE_LANDING[role] ?? '/chat';
}

export function resolvePostAuthPath(role, returnUrl) {
  const { canAccess } = useAuthStore.getState();
  if (returnUrl && returnUrl.startsWith('/') && !returnUrl.startsWith('//')) {
    const pathname = returnUrl.split('?')[0].split('#')[0];
    const pageKey = resolvePageKey(pathname);
    if (!pageKey || canAccess(pageKey, role)) {
      return returnUrl;
    }
  }
  return getDefaultRouteForRole(role);
}
