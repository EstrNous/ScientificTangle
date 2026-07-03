import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import { ROLES, useAuthStore } from '../../stores/authStore.js';

const roleOptions = Object.values(ROLES);

const PATH_PREFIX_KEYS = [
  ['/strategic', 'strategic'],
  ['/lab', 'lab'],
  ['/admin', 'admin'],
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
  return PATH_KEYS[pathname];
}

export default function RoleSwitcher() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const role = useAuthStore((s) => s.role);
  const setRole = useAuthStore((s) => s.setRole);
  const canAccess = useAuthStore((s) => s.canAccess);

  return (
    <select
      value={role}
      onChange={(e) => {
        const nextRole = e.target.value;
        setRole(nextRole);
        const pageKey = resolvePageKey(pathname);
        if (pageKey && !canAccess(pageKey, nextRole)) {
          navigate('/chat', { replace: true });
        }
      }}
      aria-label={t('common.roleSwitcher')}
      className="max-w-[11rem] cursor-pointer rounded-lg border border-nn-border bg-white px-3 py-1.5 text-sm text-gray-900 outline-none focus:border-nn-blue focus:ring-1 focus:ring-nn-blue dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
    >
      {roleOptions.map((r) => (
        <option key={r} value={r}>
          {t(`roles.${r}`)}
        </option>
      ))}
    </select>
  );
}
