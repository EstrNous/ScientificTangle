import { useTranslation } from 'react-i18next';

const STATUS_STYLES = {
  ok: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  degraded: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  down: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
};

function formatRps(value) {
  return Number(value).toLocaleString('ru-RU', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

export default function ServiceMetricsTable({ services, compact = false, fill = false }) {
  const { t } = useTranslation();

  if (!services?.length) return null;

  const cellPad = compact ? 'px-2 py-1' : 'px-2 py-2.5';
  const headPad = compact ? 'px-2 py-1.5' : 'px-2 py-2';

  return (
    <div
      className={`nn-card flex min-h-0 flex-col ${compact ? 'p-3' : 'p-4'} ${fill ? 'flex-1' : ''}`}
    >
      <div className={`flex shrink-0 items-center justify-between gap-2 ${compact ? 'mb-2' : 'mb-3'}`}>
        <p
          className={`font-semibold text-gray-900 dark:text-slate-100 ${
            compact ? 'text-xs' : 'text-sm'
          }`}
        >
          {t('admin.ops.servicesTitle')}
        </p>
      </div>
      <div className={`min-h-0 ${fill ? 'flex-1 overflow-auto' : 'overflow-x-auto'}`}>
        <table className="w-full min-w-[640px] border-collapse text-xs">
          <thead className={fill ? 'sticky top-0 z-10 bg-white dark:bg-slate-900' : ''}>
            <tr className="text-left text-nn-gray dark:text-slate-400">
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                {t('admin.ops.service')}
              </th>
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                {t('admin.ops.rps')}
              </th>
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                p50
              </th>
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                p95
              </th>
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                {t('admin.ops.errors')}
              </th>
              <th className={`border-b border-nn-border font-medium dark:border-slate-600 ${headPad}`}>
                {t('admin.ops.status')}
              </th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id} className="hover:bg-nn-gray-light/60 dark:hover:bg-slate-800/50">
                <td
                  className={`border-b border-nn-border font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100 ${cellPad}`}
                >
                  {t(`admin.ops.serviceNames.${service.id}`, { defaultValue: service.id })}
                </td>
                <td
                  className={`border-b border-nn-border tabular-nums text-gray-800 dark:border-slate-700 dark:text-slate-200 ${cellPad}`}
                >
                  {formatRps(service.rps)}
                </td>
                <td
                  className={`border-b border-nn-border tabular-nums text-nn-gray dark:border-slate-700 dark:text-slate-400 ${cellPad}`}
                >
                  {service.latency_p50_ms} ms
                </td>
                <td
                  className={`border-b border-nn-border tabular-nums text-nn-gray dark:border-slate-700 dark:text-slate-400 ${cellPad}`}
                >
                  {service.latency_p95_ms} ms
                </td>
                <td className={`border-b border-nn-border tabular-nums dark:border-slate-700 ${cellPad}`}>
                  <span
                    className={
                      service.errors_24h > 0
                        ? 'font-semibold text-amber-700 dark:text-amber-300'
                        : 'text-gray-700 dark:text-slate-300'
                    }
                  >
                    {service.errors_24h}
                  </span>
                </td>
                <td className={`border-b border-nn-border dark:border-slate-700 ${cellPad}`}>
                  <span
                    className={`inline-block rounded-full px-1.5 py-px text-[9px] font-semibold uppercase tracking-wide ${
                      STATUS_STYLES[service.status] ?? STATUS_STYLES.ok
                    }`}
                  >
                    {t(`admin.ops.statuses.${service.status}`, { defaultValue: service.status })}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
