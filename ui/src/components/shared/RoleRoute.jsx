import { Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useRoleAccess } from '../../hooks/useRoleAccess.js';

export default function RoleRoute({ paths, children }) {
  const { t } = useTranslation();
  const { canAccess } = useRoleAccess();
  const allowed = paths.some((p) => canAccess(p));

  if (!allowed) {
    return (
      <div className="h-full flex items-center justify-center text-slate-400">
        {t('common.accessDenied')}
      </div>
    );
  }

  return children;
}

export function RoleRedirect({ to = '/chat' }) {
  return <Navigate to={to} replace />;
}
