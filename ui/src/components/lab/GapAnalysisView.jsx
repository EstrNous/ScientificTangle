import { useTranslation } from 'react-i18next';
import { normalizeGap } from './normalizeGap.js';

export default function GapAnalysisView({ gaps, fill = false }) {
  const { t } = useTranslation();

  const items = (gaps ?? [])
    .map((gap, index) => normalizeGap(gap, index))
    .filter(Boolean);

  if (!items.length) return null;

  return (
    <div
      className={`nn-card flex flex-col gap-3 p-4 ${fill ? 'h-full min-h-0 overflow-hidden' : ''}`}
    >
      <p className="shrink-0 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('lab.gapsTitle')}
      </p>
      <ul
        className={`space-y-3 ${fill ? 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 overflow-y-auto pr-1' : ''}`}
      >
        {items.map((gap) => (
          <li
            key={gap.id}
            className="rounded-xl border border-amber-200 bg-amber-50/60 p-3 dark:border-amber-900/60 dark:bg-amber-950/30"
          >
            <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{gap.title}</p>
            <p className="mt-1 text-xs text-nn-gray dark:text-slate-400">{gap.description}</p>

            {gap.constraints?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {gap.constraints.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-amber-300/60 bg-white px-2 py-0.5 text-[10px] text-amber-800 dark:border-amber-800 dark:bg-slate-900 dark:text-amber-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {gap.related_cases?.length > 0 && (
              <div className="mt-3">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
                  {t('lab.relatedCases')}
                </p>
                <ul className="space-y-1">
                  {gap.related_cases.map((item) => (
                    <li
                      key={item.title}
                      className="flex items-center justify-between gap-2 text-xs text-gray-800 dark:text-slate-200"
                    >
                      <span>{item.title}</span>
                      <span className="shrink-0 tabular-nums text-nn-blue">
                        {Math.round(item.similarity * 100)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {gap.experts?.length > 0 && (
              <p className="mt-2 text-xs text-nn-gray dark:text-slate-400">
                {t('lab.experts')}: {gap.experts.join(' · ')}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
