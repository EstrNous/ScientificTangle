import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { ManagerDashboard, EvaluationDashboard } from '../components/strategic/index.js';
import { apiGet } from '../api/client.js';
import { exportStrategicPdf } from '../utils/pagePdfExport.js';

export default function StrategicPage() {
  const { t, i18n } = useTranslation();
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
      <div className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto pr-1">
        <div className="flex shrink-0 justify-end">
          <PdfDownloadButton
            onExport={() => exportStrategicPdf({ manager, evaluation, t, language: i18n.language })}
          />
        </div>
        <ManagerDashboard data={manager} />
        <EvaluationDashboard data={evaluation} />
      </div>
    </PageShell>
  );
}
