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

export default function ServiceMetricsTable({ services }) {
  const { t } = useTranslation();

  if (!services?.length) return null;

  return (
    <div className="nn-card p-4">
      <p className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('admin.ops.servicesTitle')}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-xs">
          <thead>
            <tr className="text-left text-nn-gray dark:text-slate-400">
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.ops.service')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.ops.rps')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                p50
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                p95
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.ops.errors')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.ops.status')}
              </th>
            </tr>
          </thead>
          <tbody>
            {services.map((service) => (
              <tr key={service.id} className="hover:bg-nn-gray-light/60 dark:hover:bg-slate-800/50">
                <td className="border-b border-nn-border px-2 py-2.5 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100">
                  {t(`admin.ops.serviceNames.${service.id}`, { defaultValue: service.id })}
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 tabular-nums text-gray-800 dark:border-slate-700 dark:text-slate-200">
                  {formatRps(service.rps)}
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 tabular-nums text-nn-gray dark:border-slate-700 dark:text-slate-400">
                  {service.latency_p50_ms} ms
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 tabular-nums text-nn-gray dark:border-slate-700 dark:text-slate-400">
                  {service.latency_p95_ms} ms
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 tabular-nums dark:border-slate-700">
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
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
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
