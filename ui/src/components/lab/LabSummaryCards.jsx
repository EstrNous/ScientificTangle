import { useTranslation } from 'react-i18next';

export default function LabSummaryCards({ summary }) {
  const { t } = useTranslation();

  if (!summary) return null;

  const items = [
    { key: 'gap_count', label: t('lab.summary.gaps'), accent: 'text-amber-600 dark:text-amber-400' },
    { key: 'conflict_count', label: t('lab.summary.conflicts'), accent: 'text-gray-600 dark:text-slate-400' },
    { key: 'sparse_cells', label: t('lab.summary.sparse'), accent: 'text-nn-blue' },
    { key: 'experiments_total', label: t('lab.summary.experiments'), accent: 'text-emerald-600 dark:text-emerald-400' },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {items.map(({ key, label, accent }) => (
        <div
          key={key}
          className="nn-card rounded-xl border border-nn-border p-3 dark:border-slate-700"
        >
          <p className="text-[11px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400">
            {label}
          </p>
          <p className={`mt-1 text-2xl font-bold tabular-nums ${accent}`}>
            {summary[key]?.toLocaleString('ru-RU') ?? '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
