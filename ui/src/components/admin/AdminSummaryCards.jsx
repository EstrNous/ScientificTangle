import { useTranslation } from 'react-i18next';

export default function AdminSummaryCards({ summary }) {
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
