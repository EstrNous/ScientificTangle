import { useTranslation } from 'react-i18next';

function AlertList({ title, items, tone, compact }) {
  const { t } = useTranslation();

  if (!items?.length) return null;

  const toneClass =
    tone === 'gap'
      ? 'border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40'
      : 'border-nn-border bg-nn-gray-light dark:border-slate-600 dark:bg-slate-800';

  const dotClass = tone === 'gap' ? 'bg-amber-500' : 'bg-nn-gray dark:bg-slate-400';

  return (
    <div className={`rounded-xl border p-2.5 ${toneClass}`}>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-900 dark:text-slate-100">
        {title}
      </p>
      <ul className={compact ? 'space-y-1' : 'space-y-2'}>
        {items.map((item) => (
          <li
            key={item}
            className={`flex items-start gap-2 text-gray-800 dark:text-slate-200 ${compact ? 'text-xs leading-snug' : 'text-sm'}`}
          >
            <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <p className={`mt-1.5 text-nn-gray dark:text-slate-400 ${compact ? 'text-[10px] leading-tight' : 'text-[11px]'}`}>
        {t('strategic.alertHint')}
      </p>
    </div>
  );
}

export default function TopicsAlerts({ lowCoverageTopics, highConflictTopics, fill = false }) {
  const { t } = useTranslation();

  return (
    <div
      className={`flex flex-col gap-2 ${fill ? 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 overflow-y-auto' : 'gap-3'}`}
    >
      <AlertList
        title={t('strategic.lowCoverage')}
        items={lowCoverageTopics}
        tone="gap"
        compact={fill}
      />
      <AlertList
        title={t('strategic.highConflict')}
        items={highConflictTopics}
        tone="conflict"
        compact={fill}
      />
    </div>
  );
}
