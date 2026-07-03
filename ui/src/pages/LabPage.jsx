import { useEffect, useState } from 'react';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import {
  CoverageMatrix,
  GapAnalysisView,
  GapConflictView,
  LabSummaryCards,
} from '../components/lab/index.js';
import { apiGet } from '../api/client.js';

export default function LabPage() {
  const [loading, setLoading] = useState(true);
  const [labData, setLabData] = useState(null);

  useEffect(() => {
    apiGet('/lab/coverage')
      .then(setLabData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-6 overflow-y-auto pr-1">
        <LabSummaryCards summary={labData?.summary} />
        <CoverageMatrix coverage={labData?.coverage} />
        <div className="grid min-h-0 gap-4 xl:grid-cols-2">
          <GapAnalysisView gaps={labData?.gaps} />
          <GapConflictView contradictions={labData?.contradictions} />
        </div>
      </div>
    </PageShell>
  );
}
