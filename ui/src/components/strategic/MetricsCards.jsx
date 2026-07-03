import { useTranslation } from 'react-i18next';
import { collectSourceRefs } from '../../utils/sourceRefs.js';
import { useSourceRefsPopover } from '../../hooks/useSourceRefsPopover.js';
import SourceRefsPopover from '../shared/SourceRefsPopover.jsx';

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

export default function MetricsCards({ totals, metricSources }) {
  const { t } = useTranslation();
  const { popover, openPopover, closePopover } = useSourceRefsPopover();

  if (!totals) return null;

  const handleMetricClick = (event, key) => {
    const value = totals[key];
    if (!value) return;
    const sources = collectSourceRefs(metricSources?.[key], value);
    if (!sources.length) return;
    openPopover(event, {
      title: t(`strategic.metrics.${key}`),
      subtitle: t('strategic.metricValue', { value: value.toLocaleString('ru-RU') }),
      sources,
    });
  };

  return (
    <>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        {METRIC_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={(event) => handleMetricClick(event, key)}
            className="nn-card shrink-0 rounded-xl border border-nn-border p-2.5 text-left transition-colors hover:border-nn-blue/40 hover:bg-nn-blue-light/40 dark:border-slate-700 dark:hover:border-sky-500/40 dark:hover:bg-slate-800/60"
          >
            <p className="text-[10px] font-medium uppercase leading-tight tracking-wide text-nn-gray dark:text-slate-400">
              {t(`strategic.metrics.${key}`)}
            </p>
            <p className={`mt-0.5 text-xl font-bold tabular-nums leading-none ${ACCENT[key]}`}>
              {totals[key]?.toLocaleString('ru-RU') ?? '—'}
            </p>
          </button>
        ))}
      </div>
      <SourceRefsPopover state={popover} onClose={closePopover} />
    </>
  );
}
