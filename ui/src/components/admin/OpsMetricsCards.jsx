import { useTranslation } from 'react-i18next';

function formatNumber(value, fractionDigits = 1) {
  if (value == null) return '—';
  return Number(value).toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  });
}

export default function OpsMetricsCards({ operations, compact = false, hideTitle = false }) {
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
    <div className={compact ? 'space-y-1' : 'space-y-2'}>
      {!hideTitle && (
        <div className="flex flex-wrap items-center justify-between gap-1.5">
          <p
            className={`font-semibold text-gray-900 dark:text-slate-100 ${
              compact ? 'text-[11px]' : 'text-sm'
            }`}
          >
            {t('admin.ops.title')}
          </p>
          {operations.updated_at && (
            <p className={`text-nn-gray dark:text-slate-400 ${compact ? 'text-[9px]' : 'text-xs'}`}>
              {t('admin.ops.updatedAt', {
                date: new Date(operations.updated_at).toLocaleString(),
              })}
            </p>
          )}
        </div>
      )}
      <div className={`grid grid-cols-2 gap-1.5 ${compact ? 'md:grid-cols-4' : 'gap-3 md:grid-cols-4'}`}>
        {items.map(({ key, label, value, accent }) => (
          <div
            key={key}
            className={`nn-card rounded-lg border border-nn-border dark:border-slate-700 ${
              compact ? 'px-2 py-1.5' : 'rounded-xl p-3'
            }`}
          >
            <p
              className={`font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400 ${
                compact ? 'text-[9px] leading-tight' : 'text-[11px]'
              }`}
            >
              {label}
            </p>
            <p
              className={`font-bold tabular-nums ${accent} ${
                compact ? 'mt-0.5 text-base leading-none' : 'mt-1 text-2xl'
              }`}
            >
              {value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
