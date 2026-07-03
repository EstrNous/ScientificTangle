import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { AdminSubNav, AuditLogTable, SourceViewer } from '../components/admin/index.js';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { apiGet } from '../api/client.js';
import { mergeSourceSpan } from '../api/mock/sourceCatalog.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportAdminAuditPdf } from '../utils/pagePdfExport.js';

export default function AdminAuditPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [adminData, setAdminData] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const auditExportRef = useRef(null);

  useEffect(() => {
    Promise.all([apiGet('/admin'), apiGet('/audit/events')])
      .then(([admin, events]) => {
        setAdminData(admin);
        setAuditEvents(events);
        const withSource = events.find((event) => event.source_span_id);
        setSelectedEventId(withSource?.id ?? events[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  const selectedSpan = useMemo(() => {
    const event = auditEvents.find((item) => item.id === selectedEventId);
    if (!event?.source_span_id) return null;
    const span = adminData?.source_spans?.[event.source_span_id] ?? null;
    return mergeSourceSpan(span);
  }, [auditEvents, selectedEventId, adminData]);

  const handleExportPdf = async () => {
    const auditImage = await captureElementImage(auditExportRef.current, { fullContent: true });
    await exportAdminAuditPdf({
      events: auditEvents,
      t,
      language: i18n.language,
      auditImage,
    });
  };

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
        <AdminSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        <div
          ref={auditExportRef}
          className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[1fr_360px]"
        >
          <AuditLogTable
            events={auditEvents}
            selectedId={selectedEventId}
            onSelect={(event) => setSelectedEventId(event.id)}
            fullHeight
          />
          <SourceViewer span={selectedSpan} />
        </div>
      </div>
    </PageShell>
  );
}
