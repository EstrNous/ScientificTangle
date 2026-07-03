import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const links = [
  { path: '/lab/matrix', labelKey: 'lab.nav.matrix', end: true },
  { path: '/lab/insights', labelKey: 'lab.nav.insights', end: true },
];

export default function LabSubNav({ action }) {
  const { t } = useTranslation();

  return (
    <div className="flex shrink-0 items-center justify-between gap-3 border-b border-nn-border pb-3 dark:border-slate-700">
      <nav className="flex gap-4">
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            end={link.end}
            className={({ isActive }) =>
              `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300'
                  : 'text-nn-gray hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
              }`
            }
          >
            {t(link.labelKey)}
          </NavLink>
        ))}
      </nav>
      {action}
    </div>
  );
}
