import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useRoleAccess } from '../hooks/useRoleAccess.js';

const tabs = [
  { key: 'chat', path: '/chat', labelKey: 'nav.chat' },
  { key: 'graph', path: '/graph', labelKey: 'nav.graph' },
  { key: 'strategic', path: '/strategic', labelKey: 'nav.strategic' },
  { key: 'lab', path: '/lab', labelKey: 'nav.lab' },
  { key: 'admin', path: '/admin', labelKey: 'nav.admin' },
];

export default function TabNav() {
  const { t } = useTranslation();
  const { canAccess } = useRoleAccess();

  return (
    <nav className="scrollbar-none flex shrink-0 gap-8 overflow-x-auto overflow-y-hidden border-b border-nn-border bg-white px-6 dark:border-slate-700 dark:bg-slate-900">
      {tabs
        .filter((tab) => canAccess(tab.key))
        .map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            className={({ isActive }) =>
              `whitespace-nowrap border-b-2 py-3 text-sm font-medium transition-colors -mb-px ${
                isActive
                  ? 'border-nn-blue text-nn-blue'
                  : 'border-transparent text-nn-gray hover:text-gray-900 dark:text-slate-400 dark:hover:text-slate-100'
              }`
            }
          >
            {t(tab.labelKey)}
          </NavLink>
        ))}
    </nav>
  );
}
