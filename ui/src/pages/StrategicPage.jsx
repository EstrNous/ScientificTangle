import { useEffect, useState } from 'react';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ManagerDashboard, EvaluationDashboard } from '../components/strategic/index.js';
import { apiGet } from '../api/client.js';

export default function StrategicPage() {
  const [loading, setLoading] = useState(true);
  const [manager, setManager] = useState(null);
  const [evaluation, setEvaluation] = useState(null);

  useEffect(() => {
    Promise.all([apiGet('/strategic/metrics'), apiGet('/strategic/evaluation')])
      .then(([metrics, evalData]) => {
        setManager(metrics);
        setEvaluation(evalData);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-6 overflow-y-auto pr-1">
        <ManagerDashboard data={manager} />
        <EvaluationDashboard data={evaluation} />
      </div>
    </PageShell>
  );
}
