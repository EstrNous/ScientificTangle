import { useTranslation } from 'react-i18next';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

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

export default function CoverageChart({ directions }) {
  const { t } = useTranslation();

  if (!directions?.length) return null;

  const chartData = directions.map((item) => ({
    name: item.name,
    coverage: item.coverage,
    documents: item.documents,
    coveragePct: Math.round(item.coverage * 100),
  }));

  return (
    <div className="nn-card flex min-h-0 flex-col p-4">
      <p className="mb-4 shrink-0 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('strategic.coverageTitle')}
      </p>
      <div className="min-h-[260px] flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-nn-border dark:stroke-slate-700" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: 'currentColor' }}
              angle={-28}
              textAnchor="end"
              height={64}
              interval={0}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: 'currentColor' }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CoverageTooltip />} />
            <Bar dataKey="coveragePct" fill="#0057B8" radius={[4, 4, 0, 0]} maxBarSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 space-y-2 border-t border-nn-border pt-3 dark:border-slate-700">
        {directions.map((direction) => (
          <li key={direction.id} className="flex items-center gap-3 text-xs">
            <span className="w-36 shrink-0 text-gray-900 dark:text-slate-100">{direction.name}</span>
            <div className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-nn-gray-light dark:bg-slate-800">
              <div
                className="h-full rounded-full bg-nn-blue"
                style={{ width: `${direction.coverage * 100}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right tabular-nums text-nn-gray dark:text-slate-400">
              {Math.round(direction.coverage * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
