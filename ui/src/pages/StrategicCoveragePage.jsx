import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { ManagerDashboard, StrategicSubNav } from '../components/strategic/index.js';
import { apiGet } from '../api/client.js';
import { exportStrategicCoveragePdf } from '../utils/pagePdfExport.js';

export default function StrategicCoveragePage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [manager, setManager] = useState(null);
  const coverageChartRef = useRef(null);

  useEffect(() => {
    apiGet('/strategic/metrics')
      .then(setManager)
      .finally(() => setLoading(false));
  }, []);

  const handleExportPdf = async () => {
    const chartImage = (await coverageChartRef.current?.getChartImage?.()) ?? '';
    await exportStrategicCoveragePdf({
      manager,
      t,
      language: i18n.language,
      chartImage,
    });
  };

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        <StrategicSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <ManagerDashboard data={manager} fill coverageChartRef={coverageChartRef} />
      </div>
    </PageShell>
  );
}
