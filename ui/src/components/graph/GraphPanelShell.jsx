import { useTranslation } from 'react-i18next';
import { CollapseIcon, ExpandIcon } from '../admin/AdminIcons.jsx';

export default function GraphPanelShell({
  title,
  expanded,
  onToggleExpand,
  children,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <div className={`nn-card flex min-h-0 flex-col p-3 ${expanded ? 'flex-1' : ''} ${className}`}>
      <div className="mb-2 flex shrink-0 items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {title}
        </p>
        {onToggleExpand && (
          <button
            type="button"
            onClick={onToggleExpand}
            className="rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            title={expanded ? t('graph.collapsePanel') : t('graph.expandPanel')}
            aria-label={expanded ? t('graph.collapsePanel') : t('graph.expandPanel')}
          >
            {expanded ? <CollapseIcon className="h-3.5 w-3.5" /> : <ExpandIcon className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      <div
        className={`min-h-0 ${
          expanded
            ? 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 flex-1 overflow-auto'
            : 'overflow-hidden'
        }`}
      >
        {children}
      </div>
    </div>
  );
}
