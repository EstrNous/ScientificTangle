import { useTranslation } from 'react-i18next';

function AlertList({ title, items, tone }) {
  const { t } = useTranslation();

  if (!items?.length) return null;

  const toneClass =
    tone === 'gap'
      ? 'border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/40'
      : 'border-nn-border bg-nn-gray-light dark:border-slate-600 dark:bg-slate-800';

  const dotClass = tone === 'gap' ? 'bg-amber-500' : 'bg-nn-gray dark:bg-slate-400';

  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-900 dark:text-slate-100">
        {title}
      </p>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm text-gray-800 dark:text-slate-200">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-nn-gray dark:text-slate-400">{t('strategic.alertHint')}</p>
    </div>
  );
}

export default function TopicsAlerts({ lowCoverageTopics, highConflictTopics }) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3">
      <AlertList
        title={t('strategic.lowCoverage')}
        items={lowCoverageTopics}
        tone="gap"
      />
      <AlertList
        title={t('strategic.highConflict')}
        items={highConflictTopics}
        tone="conflict"
      />
    </div>
  );
}
