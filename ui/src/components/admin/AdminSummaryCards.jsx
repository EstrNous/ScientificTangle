import { useTranslation } from 'react-i18next';

export default function AdminSummaryCards({ summary, compact = false }) {
  const { t } = useTranslation();

  if (!summary) return null;

  const items = [
    { key: 'users_count', label: t('admin.summary.users'), accent: 'text-nn-blue' },
    {
      key: 'audit_events_24h',
      label: t('admin.summary.audit24h'),
      accent: 'text-gray-700 dark:text-slate-200',
    },
    {
      key: 'restricted_documents',
      label: t('admin.summary.restricted'),
      accent: 'text-amber-600 dark:text-amber-400',
    },
    {
      key: 'access_denied_24h',
      label: t('admin.summary.denied24h'),
      accent: 'text-gray-600 dark:text-slate-400',
    },
  ];

  return (
    <div className={`grid grid-cols-2 gap-1.5 ${compact ? 'md:grid-cols-4' : 'gap-3 md:grid-cols-4'}`}>
      {items.map(({ key, label, accent }) => (
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
            {summary[key]?.toLocaleString('ru-RU') ?? '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
