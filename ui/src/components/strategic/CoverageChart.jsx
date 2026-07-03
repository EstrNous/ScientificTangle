import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { captureElementImage, waitForPaint } from '../../utils/captureElement.js';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CollapseIcon, ExpandIcon } from '../admin/AdminIcons.jsx';

function CoverageTooltip({ active, payload, label }) {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const value = payload[0]?.value;
  const docs = payload[0]?.payload?.documents;
  return (
    <div className="rounded-lg border border-nn-border bg-white px-3 py-2 text-xs shadow-card dark:border-slate-600 dark:bg-slate-800">
      <p className="font-medium text-gray-900 dark:text-slate-100">{label}</p>
      <p className="text-nn-gray dark:text-slate-400">
        {t('strategic.coverageValue', { value: Math.round(value * 100) })}
      </p>
      {docs != null && (
        <p className="text-nn-gray dark:text-slate-400">
          {t('strategic.documentsCount', { count: docs })}
        </p>
      )}
    </div>
  );
}

const CoverageChart = forwardRef(function CoverageChart({ directions, fill = false }, ref) {
  const { t } = useTranslation();
  const chartRef = useRef(null);
  const [detailsExpanded, setDetailsExpanded] = useState(false);

  useImperativeHandle(ref, () => ({
    async getChartImage() {
      const wasExpanded = detailsExpanded;
      if (wasExpanded) setDetailsExpanded(false);
      await waitForPaint();
      const image = await captureElementImage(chartRef.current);
      if (wasExpanded) setDetailsExpanded(true);
      return image;
    },
  }));

  if (!directions?.length) return null;

  const chartData = directions.map((item) => ({
    name: item.name,
    coverage: item.coverage,
    documents: item.documents,
    coveragePct: Math.round(item.coverage * 100),
  }));

  return (
    <div
      className={`nn-card flex h-full min-h-0 flex-col overflow-hidden p-3 ${fill ? 'flex-1' : ''}`}
    >
      <p className="mb-2 shrink-0 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('strategic.coverageTitle')}
      </p>

      {!detailsExpanded && (
        <div
          ref={chartRef}
          className={`min-h-0 bg-white dark:bg-slate-900 ${fill ? 'flex-1' : 'min-h-[220px] shrink-0'}`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-nn-border dark:stroke-slate-700" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: 'currentColor' }}
                angle={-28}
                textAnchor="end"
                height={48}
                interval={0}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 9, fill: 'currentColor' }}
                tickFormatter={(v) => `${v}%`}
                width={32}
              />
              <Tooltip content={<CoverageTooltip />} />
              <Bar dataKey="coveragePct" fill="#0057B8" radius={[4, 4, 0, 0]} maxBarSize={32} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div
        className={`flex flex-col border-nn-border dark:border-slate-700 ${
          detailsExpanded
            ? 'min-h-0 flex-1'
            : 'mt-1.5 shrink-0 border-t pt-1.5'
        }`}
      >
        <div className="mb-0.5 flex shrink-0 items-center justify-between gap-2">
          <p className="text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-500">
            {t('strategic.coverageList')}
          </p>
          <button
            type="button"
            onClick={() => setDetailsExpanded((prev) => !prev)}
            className="rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
            title={
              detailsExpanded ? t('strategic.collapseDetails') : t('strategic.expandDetails')
            }
            aria-label={
              detailsExpanded ? t('strategic.collapseDetails') : t('strategic.expandDetails')
            }
          >
            {detailsExpanded ? (
              <CollapseIcon className="h-3.5 w-3.5" />
            ) : (
              <ExpandIcon className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
        <div
          className={`relative min-h-0 ${
            detailsExpanded ? 'flex-1' : fill ? 'max-h-[4rem]' : 'max-h-[7.5rem]'
          }`}
        >
          <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 h-full max-h-full space-y-0.5 overflow-y-auto pr-1">
            {directions.map((direction) => (
              <li key={direction.id} className="flex items-center gap-2 text-[11px]">
                <span
                  className="w-28 shrink-0 truncate text-gray-900 dark:text-slate-100"
                  title={direction.name}
                >
                  {direction.name}
                </span>
                <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-nn-gray-light dark:bg-slate-800">
                  <div
                    className="h-full rounded-full bg-nn-blue"
                    style={{ width: `${direction.coverage * 100}%` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right tabular-nums text-nn-gray dark:text-slate-400">
                  {Math.round(direction.coverage * 100)}%
                </span>
              </li>
            ))}
          </ul>
          {!detailsExpanded && (
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-3 bg-gradient-to-t from-white to-transparent dark:from-slate-900"
              aria-hidden
            />
          )}
        </div>
        {!detailsExpanded && (
          <p className="mt-0.5 shrink-0 text-center text-[9px] text-nn-gray dark:text-slate-500">
            {t('graph.scrollHint')}
          </p>
        )}
      </div>
    </div>
  );
});

export default CoverageChart;
