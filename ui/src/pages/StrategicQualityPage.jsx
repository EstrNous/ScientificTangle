import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { EvaluationDashboard, StrategicSubNav } from '../components/strategic/index.js';
import { apiGet } from '../api/client.js';
import { exportStrategicQualityPdf } from '../utils/pagePdfExport.js';

export default function StrategicQualityPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [evaluation, setEvaluation] = useState(null);
  const evaluationRef = useRef(null);

  useEffect(() => {
    apiGet('/strategic/evaluation')
      .then(setEvaluation)
      .finally(() => setLoading(false));
  }, []);

  const handleExportPdf = async () => {
    const dashboardImage = (await evaluationRef.current?.getExportImage?.()) ?? '';
    await exportStrategicQualityPdf({
      evaluation,
      t,
      language: i18n.language,
      dashboardImage,
    });
  };

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        <StrategicSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <EvaluationDashboard ref={evaluationRef} data={evaluation} fill />
      </div>
    </PageShell>
  );
}
