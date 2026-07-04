import { useCallback, useEffect, useRef, useState } from 'react';

import { useNavigate } from 'react-router-dom';

import { useTranslation } from 'react-i18next';

import PageShell from '../components/shared/PageShell.jsx';

import Loader from '../components/shared/Loader.jsx';

import { ErrorBanner } from '../components/shared/PageState.jsx';

import { AdminSubNav, AuditLogTable, SourceViewer } from '../components/admin/index.js';

import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';

import { fetchAuditEvents } from '../api/audit.js';

import { deleteDocument } from '../api/upload.js';

import { apiGet } from '../api/client.js';

import { useSourceDocument } from '../context/SourceDocumentContext.jsx';

import { captureElementImage } from '../utils/captureElement.js';

import { exportAdminAuditPdf } from '../utils/pagePdfExport.js';

import { downloadAuditCsv } from '../utils/auditCsv.js';

import { resolveAuditEventTarget } from '../utils/auditNavigation.js';



const PAGE_SIZE = 50;

const real = { real: true };



export default function AdminAuditPage() {

  const { t, i18n } = useTranslation();

  const navigate = useNavigate();

  const { openSource } = useSourceDocument();

  const [loading, setLoading] = useState(true);

  const [loadingMore, setLoadingMore] = useState(false);

  const [auditEvents, setAuditEvents] = useState([]);

  const [selectedEventId, setSelectedEventId] = useState(null);

  const [selectedSpan, setSelectedSpan] = useState(null);

  const [deletingDocumentId, setDeletingDocumentId] = useState(null);

  const [error, setError] = useState(null);

  const [actionFilter, setActionFilter] = useState('all');

  const [hasMore, setHasMore] = useState(false);

  const auditExportRef = useRef(null);



  const loadEvents = useCallback(

    async ({ offset = 0, append = false, action = actionFilter } = {}) => {

      const apiAction = action === 'all' ? undefined : action;

      const items = await fetchAuditEvents({

        action: apiAction,

        limit: PAGE_SIZE,

        offset,

      });

      setHasMore(items.length === PAGE_SIZE);

      setAuditEvents((current) => (append ? [...current, ...items] : items));

      if (!append) {

        const withSource = items.find((event) => event.source_span_id);

        setSelectedEventId(withSource?.id ?? items[0]?.id ?? null);

      }

      return items;

    },

    [actionFilter],

  );



  useEffect(() => {

    let active = true;

    setLoading(true);

    setError(null);

    loadEvents({ offset: 0, append: false })

      .catch((loadError) => {

        if (active) setError(loadError?.message ?? 'audit_load_failed');

      })

      .finally(() => {

        if (active) setLoading(false);

      });

    return () => {

      active = false;

    };

  }, [loadEvents]);



  const selectedEvent = auditEvents.find((item) => item.id === selectedEventId) ?? null;



  useEffect(() => {

    if (!selectedEvent?.source_span_id) {

      setSelectedSpan(null);

      return;

    }

    apiGet(`/source/${encodeURIComponent(selectedEvent.source_span_id)}`, real)

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

  }, [selectedEvent]);



  const handleActionFilterChange = async (nextAction) => {

    setActionFilter(nextAction);

    setLoading(true);

    setError(null);

    try {

      const apiAction = nextAction === 'all' ? undefined : nextAction;

      const items = await fetchAuditEvents({

        action: apiAction,

        limit: PAGE_SIZE,

        offset: 0,

      });

      setHasMore(items.length === PAGE_SIZE);

      setAuditEvents(items);

      const withSource = items.find((event) => event.source_span_id);

      setSelectedEventId(withSource?.id ?? items[0]?.id ?? null);

    } catch (loadError) {

      setError(loadError?.message ?? 'audit_load_failed');

    } finally {

      setLoading(false);

    }

  };



  const handleLoadMore = async () => {

    setLoadingMore(true);

    setError(null);

    try {

      await loadEvents({ offset: auditEvents.length, append: true });

    } catch (loadError) {

      setError(loadError?.message ?? 'audit_load_failed');

    } finally {

      setLoadingMore(false);

    }

  };



  const handleDeleteDocument = async (event, documentId) => {

    const label = event.object || documentId;

    if (!window.confirm(t('admin.confirmDeleteDocument', { name: label }))) {

      return;

    }

    const snapshot = auditEvents;

    setDeletingDocumentId(documentId);

    setError(null);

    setAuditEvents((current) => current.filter((item) => item.id !== event.id));

    if (selectedEventId === event.id) {

      setSelectedEventId(null);

      setSelectedSpan(null);

    }

    try {

      await deleteDocument(documentId);

    } catch (deleteError) {

      setAuditEvents(snapshot);

      setError(deleteError?.message ?? 'delete_failed');

    } finally {

      setDeletingDocumentId(null);

    }

  };



  const handleDrillDown = async () => {

    const target = resolveAuditEventTarget(selectedEvent);

    if (target.kind === 'source') {

      await openSource(target.ref);

      return;

    }

    if (target.kind === 'navigate') {

      navigate(target.path, target.state ? { state: target.state } : undefined);

    }

  };



  const handleExportCsv = () => {

    downloadAuditCsv(auditEvents, `audit_events_${new Date().toISOString().slice(0, 10)}.csv`);

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



  const drillDownTarget = resolveAuditEventTarget(selectedEvent);

  const canDrillDown = drillDownTarget.kind !== 'none';



  return (

    <PageShell>

      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">

        <AdminSubNav

          action={

            <div className="flex items-center gap-2">

              <button

                type="button"

                onClick={handleExportCsv}

                disabled={!auditEvents.length}

                className="nn-btn-ghost text-xs disabled:cursor-not-allowed disabled:opacity-50"

              >

                {t('admin.exportCsv')}

              </button>

              <PdfDownloadButton onExport={handleExportPdf} />

            </div>

          }

        />

        {error && (
          <ErrorBanner message={t(`admin.errors.${error}`, { defaultValue: error })} />
        )}

        <div

          ref={auditExportRef}

          className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[1fr_360px]"

        >

          <div className="flex min-h-0 flex-1 flex-col gap-3">

            <AuditLogTable

              events={auditEvents}

              selectedId={selectedEventId}

              onSelect={(event) => setSelectedEventId(event.id)}

              onDeleteDocument={handleDeleteDocument}

              deletingDocumentId={deletingDocumentId}

              actionFilter={actionFilter}

              onActionFilterChange={handleActionFilterChange}

              fullHeight

            />

            {hasMore && (

              <button

                type="button"

                onClick={handleLoadMore}

                disabled={loadingMore}

                className="nn-btn-ghost self-center text-xs disabled:cursor-not-allowed disabled:opacity-50"

              >

                {loadingMore ? t('common.loading') : t('admin.loadMoreAudit')}

              </button>

            )}

          </div>

          <div className="flex min-h-0 flex-col gap-3">

            {selectedEvent && (

              <div className="nn-card shrink-0 p-4 text-xs text-gray-800 dark:text-slate-200">

                <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">

                  {t('admin.auditDetailTitle')}

                </p>

                <dl className="mt-2 space-y-1">

                  <div>

                    <dt className="text-nn-gray dark:text-slate-400">{t('admin.auditAction')}</dt>

                    <dd>{selectedEvent.action}</dd>

                  </div>

                  {selectedEvent.resource_type && (

                    <div>

                      <dt className="text-nn-gray dark:text-slate-400">{t('admin.auditResource')}</dt>

                      <dd>

                        {selectedEvent.resource_type}

                        {selectedEvent.resource_id ? `: ${selectedEvent.resource_id}` : ''}

                      </dd>

                    </div>

                  )}

                  {selectedEvent.request_id && (

                    <div>

                      <dt className="text-nn-gray dark:text-slate-400">{t('admin.auditRequestId')}</dt>

                      <dd className="break-all font-mono text-[11px]">{selectedEvent.request_id}</dd>

                    </div>

                  )}

                </dl>

                {canDrillDown && (

                  <button

                    type="button"

                    onClick={handleDrillDown}

                    className="nn-btn-ghost mt-3 w-full justify-center text-xs"

                  >

                    {t('admin.auditOpenTarget')}

                  </button>

                )}

              </div>

            )}

            <SourceViewer span={selectedSpan} />

          </div>

        </div>

      </div>

    </PageShell>

  );

}
