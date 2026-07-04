import { useTranslation } from 'react-i18next';
import { useMock } from '../../api/client.js';
import { useHealthStore } from '../../stores/healthStore.js';

const STATUS_STYLES = {
  ok: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  down: 'bg-red-500',
};

function resolveIndicatorStatus(overall, error, loading) {
  if (loading && !overall) return 'checking';
  if (error) return 'down';
  return overall ?? 'checking';
}

export default function ServiceHealthIndicator() {
  const { t } = useTranslation();
  const overall = useHealthStore((state) => state.overall);
  const peers = useHealthStore((state) => state.peers);
  const loading = useHealthStore((state) => state.loading);
  const error = useHealthStore((state) => state.error);
  const refresh = useHealthStore((state) => state.refresh);

  if (useMock) {
    return null;
  }

  const indicatorStatus = resolveIndicatorStatus(overall, error, loading);
  const dotClass = STATUS_STYLES[indicatorStatus] ?? 'bg-slate-400';

  return (
    <div className="group relative">
      <button
        type="button"
        onClick={() => refresh()}
        aria-label={t('health.label')}
        title={t(`health.statuses.${indicatorStatus}`, { defaultValue: indicatorStatus })}
        className="inline-flex items-center gap-1.5 rounded-lg border border-nn-border px-2 py-1 text-xs text-nn-gray transition-colors hover:bg-nn-gray-light dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${dotClass}`} />
        <span className="hidden sm:inline">{t('health.shortLabel')}</span>
      </button>
      <div className="pointer-events-none absolute right-0 top-full z-50 mt-2 hidden w-64 rounded-lg border border-nn-border bg-white p-3 text-left shadow-lg group-hover:pointer-events-auto group-hover:block group-focus-within:pointer-events-auto group-focus-within:block dark:border-slate-600 dark:bg-slate-900">
        <p className="mb-2 text-xs font-semibold text-gray-900 dark:text-slate-100">
          {t('health.label')}
        </p>
        {error && (
          <p className="mb-2 text-xs text-red-600 dark:text-red-400">
            {t('health.checkFailed')}
          </p>
        )}
        <ul className="max-h-48 space-y-1 overflow-y-auto text-xs">
          {peers.map((peer) => (
            <li key={peer.service} className="flex items-center justify-between gap-2">
              <span className="truncate text-gray-900 dark:text-slate-100">
                {t(`admin.ops.serviceNames.${peer.service}`, { defaultValue: peer.service })}
              </span>
              <span
                className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium uppercase ${
                  peer.status === 'ok'
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200'
                    : peer.status === 'degraded'
                      ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200'
                      : 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200'
                }`}
              >
                {t(`admin.ops.statuses.${peer.status}`, { defaultValue: peer.status })}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
