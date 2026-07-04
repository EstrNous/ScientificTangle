import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMock } from '../../api/client.js';
import { requestExport } from '../../api/export.js';
import {
  buildReportPayload,
  downloadJsonReport,
  downloadMarkdownReport,
  downloadPdfReport,
} from '../../utils/reportExport.js';
import {
  downloadExportPayload,
  isExportProcessing,
  wait,
  EXPORT_POLL_INTERVAL_MS,
  EXPORT_POLL_MAX_ATTEMPTS,
} from '../../utils/exportDelivery.js';
import { isClientExportFallbackEnabled } from '../../utils/uiFeatureFlags.js';

const SERVER_FORMATS = {
  md: 'markdown',
  markdown: 'markdown',
  json: 'json',
};

function resolveQueryRunId(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const runId = messages[index]?.query_run_id;
    if (runId) return runId;
  }
  return null;
}

function useClientSideExport() {
  if (useMock) {
    return isClientExportFallbackEnabled();
  }
  return isClientExportFallbackEnabled();
}

function useServerExport() {
  if (useMock) {
    return !isClientExportFallbackEnabled();
  }
  return true;
}

export default function ExportPanel({ sessionId, sessionTitle, messages = [], inline = false }) {
  const { t } = useTranslation();
  const [activeFormat, setActiveFormat] = useState(null);
  const [error, setError] = useState(null);

  const queryRunId = resolveQueryRunId(messages);
  const clientExportEnabled = useClientSideExport();
  const serverExportEnabled = useServerExport();
  const payload = buildReportPayload(sessionId, sessionTitle, messages);

  const runClientExport = async (format) => {
    if (format === 'md') {
      downloadMarkdownReport(payload);
      return;
    }
    if (format === 'json') {
      downloadJsonReport(payload);
      return;
    }
    if (format === 'pdf') {
      await downloadPdfReport(payload);
    }
  };

  const runServerExport = async (format) => {
    if (!queryRunId) {
      throw new Error('export_no_query_run');
    }
    const apiFormat = SERVER_FORMATS[format];
    if (!apiFormat) {
      throw new Error('export_format_unavailable');
    }

    let result = await requestExport({ queryRunId, format: apiFormat });
    let attempts = 0;
    while (isExportProcessing(result.status) && attempts < EXPORT_POLL_MAX_ATTEMPTS) {
      await wait(EXPORT_POLL_INTERVAL_MS);
      attempts += 1;
      result = await requestExport({ queryRunId, format: apiFormat });
    }

    if (isExportProcessing(result.status)) {
      throw new Error('export_still_processing');
    }

    downloadExportPayload(result, { fallbackName: `report_${queryRunId}` });
  };

  const handleExport = async (format) => {
    if (!sessionId) return;
    setError(null);
    setActiveFormat(format);
    try {
      if (format === 'jsonld') {
        throw new Error('export_jsonld_unavailable');
      }
      if (format === 'pdf' && serverExportEnabled) {
        throw new Error('export_pdf_unavailable');
      }
      if (serverExportEnabled && format !== 'pdf') {
        await runServerExport(format);
        return;
      }
      if (clientExportEnabled || format === 'pdf') {
        await runClientExport(format);
        return;
      }
      throw new Error('export_backend_required');
    } catch (exportError) {
      setError(exportError?.message ?? 'export_failed');
    } finally {
      setActiveFormat(null);
    }
  };

  const disabled = !sessionId || (serverExportEnabled && !queryRunId && !clientExportEnabled);
  const jsonLdUnavailable = true;
  const pdfServerUnavailable = serverExportEnabled;

  const content = (
    <>
      <p className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('chat.export')}
      </p>
      {serverExportEnabled && !queryRunId && (
        <p className="mb-2 text-xs text-amber-700 dark:text-amber-300">{t('chat.exportNeedsRun')}</p>
      )}
      {error && (
        <p className="mb-2 text-xs text-red-600 dark:text-red-400">
          {t(`chat.exportErrors.${error}`, { defaultValue: error })}
        </p>
      )}
      <div className="flex flex-col gap-2">
        <button
          type="button"
          disabled={disabled || activeFormat === 'md'}
          onClick={() => handleExport('md')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          {activeFormat === 'md' ? t('chat.exporting') : t('chat.downloadMd')}
        </button>
        <button
          type="button"
          disabled={disabled || activeFormat === 'json'}
          onClick={() => handleExport('json')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          {activeFormat === 'json' ? t('chat.exporting') : t('chat.downloadJson')}
        </button>
        <button
          type="button"
          disabled
          title={t('chat.exportJsonLdUnavailable')}
          className="nn-btn-ghost w-full justify-center text-xs opacity-50"
        >
          {t('chat.downloadJsonLd')}
          {jsonLdUnavailable && (
            <span className="ml-1 text-[10px] text-nn-gray dark:text-slate-500">
              ({t('chat.exportUnavailable')})
            </span>
          )}
        </button>
        <button
          type="button"
          disabled={disabled || pdfServerUnavailable || activeFormat === 'pdf'}
          onClick={() => handleExport('pdf')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
          title={pdfServerUnavailable ? t('chat.exportPdfUnavailable') : undefined}
        >
          {activeFormat === 'pdf' ? t('chat.downloadingPdf') : t('chat.downloadPdf')}
          {pdfServerUnavailable && (
            <span className="ml-1 text-[10px] text-nn-gray dark:text-slate-500">
              ({t('chat.exportUnavailable')})
            </span>
          )}
        </button>
      </div>
    </>
  );

  if (inline) return <div className="shrink-0">{content}</div>;

  return <div className="nn-card shrink-0 p-4">{content}</div>;
}
