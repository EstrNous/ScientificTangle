import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { GapAnalysisView, GapConflictView, LabSubNav } from '../components/lab/index.js';
import { ensureAuth } from '../api/auth.js';
import { getApiErrorMessage } from '../api/errors.js';
import { fetchLabCoverage } from '../api/lab.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportLabInsightsPdf } from '../utils/pagePdfExport.js';

export default function LabInsightsPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [labData, setLabData] = useState(null);
  const insightsRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        await ensureAuth();
        const data = await fetchLabCoverage();
        if (!cancelled) setLabData(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError, 'lab_load_failed'));
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
    const insightsImage = await captureElementImage(insightsRef.current, { fullContent: true });
    await exportLabInsightsPdf({
      labData,
      t,
      language: i18n.language,
      insightsImage,
    });
  };

  if (loading) return <Loader />;

  if (error) {
    return (
      <PageShell>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {t(`lab.errors.${error}`, { defaultValue: error })}
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        <LabSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <div
          ref={insightsRef}
          className="grid min-h-0 flex-1 gap-4 xl:grid-cols-2"
        >
          <GapAnalysisView gaps={labData?.gaps} fill />
          <GapConflictView contradictions={labData?.contradictions} fill />
        </div>
      </div>
    </PageShell>
  );
}
