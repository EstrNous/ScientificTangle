import { useTranslation } from 'react-i18next';

function formatNumber(value, fractionDigits = 1) {
  if (value == null) return '—';
  return Number(value).toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  });
}

export default function OpsMetricsCards({ operations }) {
  const { t } = useTranslation();

  if (!operations) return null;

  const items = [
    {
      key: 'latency_p50_ms',
      label: t('admin.ops.latencyP50'),
      value: `${formatNumber(operations.latency_p50_ms, 0)} ms`,
      accent: 'text-nn-blue',
    },
    {
      key: 'latency_p95_ms',
      label: t('admin.ops.latencyP95'),
      value: `${formatNumber(operations.latency_p95_ms, 0)} ms`,
      accent: 'text-sky-600 dark:text-sky-400',
    },
    {
      key: 'errors_24h',
      label: t('admin.ops.errors24h'),
      value: formatNumber(operations.errors_24h, 0),
      accent:
        operations.errors_24h > 0
          ? 'text-amber-600 dark:text-amber-400'
          : 'text-emerald-600 dark:text-emerald-400',
    },
    {
      key: 'rps_total',
      label: t('admin.ops.rpsTotal'),
      value: formatNumber(operations.rps_total),
      accent: 'text-gray-800 dark:text-slate-100',
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('admin.ops.title')}
        </p>
        {operations.updated_at && (
          <p className="text-xs text-nn-gray dark:text-slate-400">
            {t('admin.ops.updatedAt', {
              date: new Date(operations.updated_at).toLocaleString(),
            })}
          </p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {items.map(({ key, label, value, accent }) => (
          <div
            key={key}
            className="nn-card rounded-xl border border-nn-border p-3 dark:border-slate-700"
          >
            <p className="text-[11px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400">
              {label}
            </p>
            <p className={`mt-1 text-2xl font-bold tabular-nums ${accent}`}>{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
