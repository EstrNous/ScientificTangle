import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { EmptyState } from './PageState.jsx';
import Loader from './Loader.jsx';
import { useRoleAccess } from '../../hooks/useRoleAccess.js';
import { useAuthStore } from '../../stores/authStore.js';
import { getDefaultRouteForRole } from '../../utils/authNavigation.js';

export default function RoleRoute({ paths, children }) {
  const { t } = useTranslation();
  const { canAccess } = useRoleAccess();
  const role = useAuthStore((s) => s.role);
  const allowed = paths.some((p) => canAccess(p));

  if (role == null) {
    return <Loader />;
  }

  if (!allowed) {
    return (
      <EmptyState
        className="h-full"
        title={t('common.accessDenied')}
        message={t('common.accessDeniedHint')}
      />
    );
  }

  return children;
}

export function RoleRedirect({ to = '/chat' }) {
  return <Navigate to={to} replace />;
}

export function RoleLandingRedirect() {
  const role = useAuthStore((s) => s.role);
  if (role == null) {
    return <Loader />;
  }
  return <Navigate to={getDefaultRouteForRole(role)} replace />;
}
