import { useTranslation } from 'react-i18next';

export default function LabSummaryCards({ summary }) {
  const { t } = useTranslation();

  if (!summary) return null;

  const items = [
    { key: 'gap_count', label: t('lab.summary.gaps'), accent: 'text-amber-600 dark:text-amber-400' },
    { key: 'conflict_count', label: t('lab.summary.conflicts'), accent: 'text-gray-600 dark:text-slate-400' },
    { key: 'sparse_cells', label: t('lab.summary.sparse'), accent: 'text-nn-blue' },
    { key: 'links_total', label: t('lab.summary.links'), accent: 'text-emerald-600 dark:text-emerald-400' },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
      {items.map(({ key, label, accent }) => (
        <div
          key={key}
          className="nn-card rounded-lg border border-nn-border px-2.5 py-1.5 dark:border-slate-700"
        >
          <p className="text-[9px] font-medium uppercase leading-tight tracking-wide text-nn-gray dark:text-slate-400">
            {label}
          </p>
          <p className={`mt-0.5 text-lg font-bold leading-none tabular-nums ${accent}`}>
            {summary[key]?.toLocaleString('ru-RU') ?? '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
