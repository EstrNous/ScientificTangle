import { useTranslation } from 'react-i18next';
import MetricsCards from './MetricsCards.jsx';
import CoverageChart from './CoverageChart.jsx';
import TopicsAlerts from './TopicsAlerts.jsx';

export default function ManagerDashboard({ data, fill = false, coverageChartRef }) {
  const { t } = useTranslation();

  if (!data) return null;

  return (
    <div
      className={
        fill ? 'flex min-h-0 flex-1 flex-col gap-2 overflow-hidden' : 'space-y-4'
      }
    >
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('strategic.managerTitle')}
        </p>
        {data.updated_at && (
          <p className="text-xs text-nn-gray dark:text-slate-400">
            {t('strategic.updatedAt', {
              date: new Date(data.updated_at).toLocaleString(),
            })}
          </p>
        )}
      </div>
      <MetricsCards totals={data.totals} />
      <div
        className={`grid min-h-0 gap-3 ${fill ? 'h-full min-h-0 flex-1 xl:grid-cols-[1fr_260px]' : 'xl:grid-cols-[1fr_280px]'}`}
      >
        <div className="flex h-full min-h-0 flex-col">
          <CoverageChart ref={coverageChartRef} directions={data.directions} fill={fill} />
        </div>
        <div className="min-h-0">
          <TopicsAlerts
            lowCoverageTopics={data.low_coverage_topics}
            highConflictTopics={data.high_conflict_topics}
            fill={fill}
          />
        </div>
      </div>
    </div>
  );
}
