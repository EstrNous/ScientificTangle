import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { canDeleteAuditDocument, resolveDocumentIdFromAuditEvent } from '../../api/upload.js';
import AdminPanelShell from './AdminPanelShell.jsx';
import { DeleteIcon } from './AdminIcons.jsx';

const ACTION_FILTERS = [
  'all',
  'query_created',
  'source_viewed',
  'document_exported',
  'access_denied',
  'ingestion_upload',
  'role_changed',
];

function formatTime(iso, locale) {
  try {
    return new Date(iso).toLocaleString(locale === 'en' ? 'en-GB' : 'ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function AuditLogTable({
  events,
  selectedId,
  onSelect,
  onDeleteDocument,
  deletingDocumentId,
  fullHeight = false,
}) {
  const { t, i18n } = useTranslation();
  const [actionFilter, setActionFilter] = useState('all');

  const filtered = useMemo(() => {
    if (actionFilter === 'all') return events ?? [];
    return (events ?? []).filter((event) => event.action === actionFilter);
  }, [events, actionFilter]);

  if (!events?.length) return null;

  const filterSelect = (
    <select
      value={actionFilter}
      onChange={(e) => setActionFilter(e.target.value)}
      className="rounded-lg border border-nn-border bg-white px-2 py-1 text-xs text-gray-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
    >
      {ACTION_FILTERS.map((action) => (
        <option key={action} value={action}>
          {action === 'all' ? t('admin.filterAll') : t(`admin.actions.${action}`)}
        </option>
      ))}
    </select>
  );

  return (
    <AdminPanelShell
      title={t('admin.auditTitle')}
      toolbar={filterSelect}
      expanded={fullHeight}
      className={fullHeight ? 'min-h-0 flex-1' : 'min-h-0'}
    >
      <div className={fullHeight ? 'min-h-0' : 'max-h-72 overflow-auto'}>
        <table className="w-full min-w-[640px] border-collapse text-xs">
          <thead className="sticky top-0 bg-white dark:bg-slate-900">
            <tr className="text-left text-nn-gray dark:text-slate-400">
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.auditTime')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.auditUser')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.auditAction')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.auditObject')}
              </th>
              <th className="w-10 border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                <span className="sr-only">{t('admin.auditActions')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((event) => {
              const documentId = resolveDocumentIdFromAuditEvent(event);
              const canDelete = canDeleteAuditDocument(event);
              return (
                <tr
                  key={event.id}
                  onClick={() => onSelect?.(event)}
                  className={`cursor-pointer transition-colors ${
                    selectedId === event.id
                      ? 'bg-nn-blue-light dark:bg-slate-800'
                      : 'hover:bg-nn-gray-light dark:hover:bg-slate-800/60'
                  }`}
                >
                  <td className="border-b border-nn-border px-2 py-2 tabular-nums text-nn-gray dark:border-slate-700 dark:text-slate-400">
                    {formatTime(event.timestamp, i18n.language)}
                  </td>
                  <td className="border-b border-nn-border px-2 py-2 dark:border-slate-700">
                    <p className="font-medium text-gray-900 dark:text-slate-100">{event.user}</p>
                    <p className="text-[10px] text-nn-gray dark:text-slate-500">
                      {t(`roles.${event.role}`)}
                    </p>
                  </td>
                  <td className="border-b border-nn-border px-2 py-2 dark:border-slate-700">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        event.action === 'access_denied'
                          ? 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300'
                          : 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300'
                      }`}
                    >
                      {t(`admin.actions.${event.action}`, { defaultValue: event.action })}
                    </span>
                  </td>
                  <td className="border-b border-nn-border px-2 py-2 text-gray-800 dark:border-slate-700 dark:text-slate-200">
                    {event.object}
                  </td>
                  <td className="border-b border-nn-border px-2 py-2 text-center dark:border-slate-700">
                    {canDelete && onDeleteDocument && (
                      <button
                        type="button"
                        onClick={(clickEvent) => {
                          clickEvent.stopPropagation();
                          onDeleteDocument(event, documentId);
                        }}
                        disabled={deletingDocumentId === documentId}
                        className="inline-flex rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                        title={t('admin.deleteDocument')}
                        aria-label={t('admin.deleteDocument')}
                      >
                        <DeleteIcon className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </AdminPanelShell>
  );
}
