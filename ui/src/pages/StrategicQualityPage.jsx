import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ErrorBanner } from '../components/shared/PageState.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { EvaluationDashboard, StrategicSubNav } from '../components/strategic/index.js';
import { ensureAuth } from '../api/auth.js';
import { fetchStrategicEvaluation } from '../api/strategic.js';
import { fetchEvalReportSummary } from '../api/eval.js';
import { exportStrategicQualityPdf } from '../utils/pagePdfExport.js';

function getApiErrorMessage(error, fallback) {
  return error?.response?.data?.message ?? error?.message ?? fallback;
}

export default function StrategicQualityPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [reportMeta, setReportMeta] = useState(null);
  const evaluationRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        await ensureAuth();
        const [data, summary] = await Promise.all([
          fetchStrategicEvaluation(),
          fetchEvalReportSummary().catch(() => null),
        ]);
        if (!cancelled) {
          setEvaluation(data);
          setReportMeta(summary);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError, 'strategic_load_failed'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
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

  if (error) {
    return (
      <PageShell>
        <ErrorBanner message={error} />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        <StrategicSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <EvaluationDashboard ref={evaluationRef} data={evaluation} reportMeta={reportMeta} fill />
      </div>
    </PageShell>
  );
}
