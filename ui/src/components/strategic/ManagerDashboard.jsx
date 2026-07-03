import { useTranslation } from 'react-i18next';
import MetricsCards from './MetricsCards.jsx';
import CoverageChart from './CoverageChart.jsx';
import TopicsAlerts from './TopicsAlerts.jsx';

export default function ManagerDashboard({ data }) {
  const { t } = useTranslation();

  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
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
      <div className="grid min-h-0 gap-4 xl:grid-cols-[1fr_280px]">
        <CoverageChart directions={data.directions} />
        <TopicsAlerts
          lowCoverageTopics={data.low_coverage_topics}
          highConflictTopics={data.high_conflict_topics}
        />
      </div>
    </div>
  );
}
