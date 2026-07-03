import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { GapAnalysisView, GapConflictView, LabSubNav } from '../components/lab/index.js';
import { apiGet } from '../api/client.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportLabInsightsPdf } from '../utils/pagePdfExport.js';

export default function LabInsightsPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [labData, setLabData] = useState(null);
  const insightsRef = useRef(null);

  useEffect(() => {
    apiGet('/lab/coverage')
      .then(setLabData)
      .finally(() => setLoading(false));
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
