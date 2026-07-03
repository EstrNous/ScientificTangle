import { useTranslation } from 'react-i18next';

const METRIC_KEYS = [
  'documents',
  'claims',
  'verified_claims',
  'candidates',
  'gaps',
  'conflicts',
];

const ACCENT = {
  documents: 'text-nn-blue',
  claims: 'text-sky-600 dark:text-sky-400',
  verified_claims: 'text-emerald-600 dark:text-emerald-400',
  candidates: 'text-amber-600 dark:text-amber-400',
  gaps: 'text-orange-600 dark:text-orange-400',
  conflicts: 'text-gray-600 dark:text-slate-400',
};

export default function MetricsCards({ totals }) {
  const { t } = useTranslation();

  if (!totals) return null;

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
      {METRIC_KEYS.map((key) => (
        <div
          key={key}
          className="nn-card shrink-0 rounded-xl border border-nn-border p-2.5 dark:border-slate-700"
        >
          <p className="text-[10px] font-medium uppercase leading-tight tracking-wide text-nn-gray dark:text-slate-400">
            {t(`strategic.metrics.${key}`)}
          </p>
          <p className={`mt-0.5 text-xl font-bold tabular-nums leading-none ${ACCENT[key]}`}>
            {totals[key]?.toLocaleString('ru-RU') ?? '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
