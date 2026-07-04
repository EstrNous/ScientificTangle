import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { AdminSubNav, AuditLogTable, SourceViewer } from '../components/admin/index.js';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { apiGet } from '../api/client.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportAdminAuditPdf } from '../utils/pagePdfExport.js';

const real = { real: true };

export default function AdminAuditPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [auditEvents, setAuditEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const auditExportRef = useRef(null);

  useEffect(() => {
    Promise.all([apiGet('/audit/events', real)])
      .then(([events]) => {
        setAuditEvents(events);
        const withSource = events.find((event) => event.source_span_id);
        setSelectedEventId(withSource?.id ?? events[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const event = auditEvents.find((item) => item.id === selectedEventId);
    if (!event?.source_span_id) {
      setSelectedSpan(null);
      return;
    }
    apiGet(`/source/${encodeURIComponent(event.source_span_id)}`, real)
      .then((payload) => {
        const span = payload?.source_span ?? {};
        setSelectedSpan({
          id: span.id,
          title: payload?.document_title ?? span.document_id,
          page: span.page,
          raw_text: span.text,
          highlight: span.text,
        });
      })
      .catch(() => setSelectedSpan(null));
  }, [auditEvents, selectedEventId]);

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
