import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { AdminSubNav, AuditLogTable, SourceViewer } from '../components/admin/index.js';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { apiGet } from '../api/client.js';
import { deleteDocument } from '../api/upload.js';
import { captureElementImage } from '../utils/captureElement.js';
import { exportAdminAuditPdf } from '../utils/pagePdfExport.js';

const real = { real: true };

export default function AdminAuditPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [auditEvents, setAuditEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [selectedSpan, setSelectedSpan] = useState(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState(null);
  const [error, setError] = useState(null);
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

  const handleDeleteDocument = async (event, documentId) => {
    const label = event.object || documentId;
    if (!window.confirm(t('admin.confirmDeleteDocument', { name: label }))) {
      return;
    }
    setDeletingDocumentId(documentId);
    setError(null);
    try {
      await deleteDocument(documentId);
      setAuditEvents((current) => current.filter((item) => item.id !== event.id));
      if (selectedEventId === event.id) {
        setSelectedEventId(null);
        setSelectedSpan(null);
      }
    } catch (deleteError) {
      setError(deleteError?.message ?? 'delete_failed');
    } finally {
      setDeletingDocumentId(null);
    }
  };

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
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">
            {t(`upload.errors.${error}`, { defaultValue: error })}
          </p>
        )}
        <div
          ref={auditExportRef}
          className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[1fr_360px]"
        >
          <AuditLogTable
            events={auditEvents}
            selectedId={selectedEventId}
            onSelect={(event) => setSelectedEventId(event.id)}
            onDeleteDocument={handleDeleteDocument}
            deletingDocumentId={deletingDocumentId}
            fullHeight
          />
          <SourceViewer span={selectedSpan} />
        </div>
      </div>
    </PageShell>
  );
}
