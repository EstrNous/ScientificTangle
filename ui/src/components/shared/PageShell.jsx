import { useTranslation } from 'react-i18next';

export default function PageShell({ title, subtitle, children, aside, hideHeading = false }) {
  const { t } = useTranslation();

  return (
    <div className="flex h-full min-h-0 flex-col">
      {title && (
        <nav className="mb-2 shrink-0 text-xs text-nn-gray dark:text-slate-400">
          <span>{t('common.home')}</span>
          <span className="mx-1.5">›</span>
          <span className="text-gray-900 dark:text-slate-100">{title}</span>
        </nav>
      )}
      {title && !hideHeading && (
        <div className="mb-4 shrink-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-slate-100">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-nn-gray dark:text-slate-400">{subtitle}</p>}
        </div>
      )}
      <div className="flex min-h-0 flex-1 gap-4">
        <div className="nn-card min-h-0 flex-1 overflow-hidden p-4">{children}</div>
        {aside && (
          <aside className="flex w-80 shrink-0 min-h-0 flex-col gap-3 overflow-auto">
            {aside}
          </aside>
        )}
      </div>
    </div>
  );
}
