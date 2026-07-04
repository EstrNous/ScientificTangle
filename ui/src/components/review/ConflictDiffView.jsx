import { useTranslation } from 'react-i18next';
import SourceLink from '../shared/SourceLink.jsx';

export default function ConflictDiffView({ conflicts }) {
  const { t } = useTranslation();

  if (!conflicts?.length) {
    return (
      <div className="nn-card p-4 text-sm text-nn-gray dark:text-slate-400">{t('review.noConflicts')}</div>
    );
  }

  return (
    <div className="nn-card flex min-h-0 flex-col gap-3 p-4">
      <p className="shrink-0 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('review.conflictsTitle')}
      </p>
      <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {conflicts.map((item) => (
          <li
            key={item.id}
            className="rounded-xl border border-nn-border bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
          >
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
              {item.id}
            </p>
            <div className="grid gap-2 text-xs md:grid-cols-2">
              <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 dark:border-slate-600 dark:bg-slate-800">
                <p className="font-medium text-gray-900 dark:text-slate-100">{item.claimA}</p>
                <p className="mt-1 text-nn-gray dark:text-slate-400">{item.conditionA}</p>
                <p className="mt-1 text-[11px]">
                  <SourceLink sourceRef={item.sourceA} />
                </p>
              </div>
              <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 dark:border-slate-600 dark:bg-slate-800">
                <p className="font-medium text-gray-900 dark:text-slate-100">{item.claimB}</p>
                <p className="mt-1 text-nn-gray dark:text-slate-400">{item.conditionB}</p>
                <p className="mt-1 text-[11px]">
                  <SourceLink sourceRef={item.sourceB} />
                </p>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
