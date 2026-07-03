import { useTranslation } from 'react-i18next';
import { CollapseIcon, ExpandIcon } from './AdminIcons.jsx';

export default function AdminPanelShell({
  title,
  expanded,
  onToggleExpand,
  toolbar,
  children,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <div className={`nn-card flex min-h-0 flex-1 flex-col p-4 ${className}`}>
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{title}</p>
        <div className="flex items-center gap-2">
          {toolbar}
          {onToggleExpand && (
            <button
              type="button"
              onClick={onToggleExpand}
              className="rounded-md p-1.5 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              title={expanded ? t('admin.collapsePanel') : t('admin.expandPanel')}
              aria-label={expanded ? t('admin.collapsePanel') : t('admin.expandPanel')}
            >
              {expanded ? <CollapseIcon /> : <ExpandIcon />}
            </button>
          )}
        </div>
      </div>
      <div className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 overflow-auto pt-3">
        {children}
      </div>
    </div>
  );
}
