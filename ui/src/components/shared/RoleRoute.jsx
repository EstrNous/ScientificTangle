import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { EmptyState } from './PageState.jsx';
import { useRoleAccess } from '../../hooks/useRoleAccess.js';

export default function RoleRoute({ paths, children }) {
  const { t } = useTranslation();
  const { canAccess } = useRoleAccess();
  const allowed = paths.some((p) => canAccess(p));

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
