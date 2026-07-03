import { useAuthStore } from '../stores/authStore.js';

export function useRoleAccess() {
  const role = useAuthStore((s) => s.role);
  const canAccess = useAuthStore((s) => s.canAccess);

  return {
    role,
    canAccess: (pageKey) => canAccess(pageKey, role),
  };
}
