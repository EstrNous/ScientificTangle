import { useTranslation } from 'react-i18next';
import { DeleteIcon } from '../admin/AdminIcons.jsx';
import Loader from '../shared/Loader.jsx';

const TASK_STATUS_STYLES = {
  pending: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  processing: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
  completed: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300',
  failed: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300',
};

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-nn-border bg-nn-gray-light/50 px-3 py-2 dark:border-slate-600 dark:bg-slate-800/60">
      <p className="text-[10px] uppercase tracking-wide text-nn-gray dark:text-slate-400">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900 dark:text-slate-100">{value}</p>
    </div>
  );
}

export default function UploadAnalysisPanel({
  task,
  loading,
  uploadedDocuments = [],
  onDeleteDocument,
  deletingDocumentId,
}) {
  const { t } = useTranslation();
  const report = task?.report;

  return (
    <section className="nn-card flex min-h-0 flex-col p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">{t('upload.analysisTitle')}</h3>

      {loading && !task && (
        <div className="flex flex-1 items-center justify-center py-8">
          <Loader />
        </div>
      )}

      {!loading && !task && (
        <p className="text-sm text-nn-gray dark:text-slate-400">{t('upload.analysisEmpty')}</p>
      )}

      {task && (
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs text-nn-gray dark:text-slate-400">{t('upload.taskStatus')}</span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide ${
                TASK_STATUS_STYLES[task.status] ?? TASK_STATUS_STYLES.pending
              }`}
            >
              {t(`upload.taskStatuses.${task.status}`, { defaultValue: task.status })}
            </span>
          </div>

          {loading && task.status !== 'completed' && task.status !== 'failed' && <Loader />}

          {report && (
            <div className="grid grid-cols-2 gap-2">
              <Metric label={t('upload.metrics.documents')} value={report.documents_count ?? 0} />
              <Metric label={t('upload.metrics.spans')} value={report.source_spans_count ?? 0} />
              <Metric label={t('upload.metrics.tables')} value={report.tables_count ?? 0} />
              <Metric label={t('upload.metrics.claims')} value={report.extracted_claims_count ?? 0} />
              <Metric label={t('upload.metrics.candidates')} value={report.candidates_count ?? 0} />
              <Metric label={t('upload.metrics.indexed')} value={report.indexed_points_count ?? 0} />
            </div>
          )}

          {uploadedDocuments.length > 0 && (
            <div className="min-h-0">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400">
                {t('upload.sourcesTitle')}
              </p>
              <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-28 space-y-1 overflow-y-auto pr-1 text-xs">
                {uploadedDocuments.map((document) => (
                  <li
                    key={document.id}
                    className="flex items-center gap-2 rounded-md bg-nn-gray-light px-2 py-1 text-gray-900 dark:bg-slate-800 dark:text-slate-100"
                  >
                    <span className="min-w-0 flex-1 truncate" title={document.filename}>
                      {document.filename}
                    </span>
                    <span className="shrink-0 rounded-full bg-white px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-nn-gray dark:bg-slate-900 dark:text-slate-400">
                      {t(`upload.fileKinds.${document.kind}`, { defaultValue: document.kind })}
                    </span>
                    {onDeleteDocument && (
                      <button
                        type="button"
                        onClick={() => onDeleteDocument(document)}
                        disabled={deletingDocumentId === document.id}
                        className="inline-flex shrink-0 rounded-md p-1 text-nn-gray transition-colors hover:bg-white hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-100"
                        title={t('upload.deleteDocument')}
                        aria-label={t('upload.deleteDocument')}
                      >
                        <DeleteIcon className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report?.warnings?.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-amber-700 dark:text-amber-300">
                {t('upload.warningsTitle')}
              </p>
              <ul className="space-y-1 text-xs text-amber-800 dark:text-amber-200">
                {report.warnings.map((warning) => (
                  <li key={warning} className="rounded-md bg-amber-50 px-2 py-1 dark:bg-amber-950/40">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {task.error_message && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {task.error_message}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
