import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import {
  AdminSubNav,
  AdminSummaryCards,
  OpsMetricsCards,
  ServiceMetricsTable,
} from '../components/admin/index.js';
import { apiGet } from '../api/client.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportAdminStatsPdf } from '../utils/pagePdfExport.js';

export default function AdminStatsPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [adminData, setAdminData] = useState(null);
  const statsVisualRef = useRef(null);

  useEffect(() => {
    apiGet('/admin')
      .then(setAdminData)
      .finally(() => setLoading(false));
  }, []);

  const summary = useMemo(() => {
    if (!adminData?.summary) return null;
    const usersCount = adminData.users?.length ?? adminData.summary.users_count;
    return { ...adminData.summary, users_count: usersCount };
  }, [adminData]);

  const handleExportPdf = async () => {
    const dashboardImage = await captureElementImage(statsVisualRef.current, { fullContent: true });
    await exportAdminStatsPdf({
      adminData,
      t,
      language: i18n.language,
      dashboardImage,
    });
  };

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        <AdminSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <div
          ref={statsVisualRef}
          className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden"
        >
          <AdminSummaryCards summary={summary} />
          <OpsMetricsCards operations={adminData?.operations} />
          <ServiceMetricsTable services={adminData?.operations?.services} fill />
        </div>
      </div>
    </PageShell>
  );
}
