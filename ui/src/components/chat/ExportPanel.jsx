import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  buildReportPayload,
  downloadJsonReport,
  downloadMarkdownReport,
  downloadPdfReport,
} from '../../utils/reportExport.js';

export default function ExportPanel({ sessionId, sessionTitle, messages = [], inline = false }) {
  const { t } = useTranslation();
  const [exportingPdf, setExportingPdf] = useState(false);

  const payload = buildReportPayload(sessionId, sessionTitle, messages);

  const handleExport = async (format) => {
    if (!sessionId) return;
    if (format === 'md') {
      downloadMarkdownReport(payload);
      return;
    }
    if (format === 'json') {
      downloadJsonReport(payload);
      return;
    }
    if (format === 'pdf') {
      setExportingPdf(true);
      try {
        await downloadPdfReport(payload);
      } finally {
        setExportingPdf(false);
      }
    }
  };

  const disabled = !sessionId;

  const content = (
    <>
      <p className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('chat.export')}
      </p>
      <div className="flex flex-col gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => handleExport('md')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('chat.downloadMd')}
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => handleExport('json')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          {t('chat.downloadJson')}
        </button>
        <button
          type="button"
          disabled={disabled || exportingPdf}
          onClick={() => handleExport('pdf')}
          className="nn-btn-ghost w-full justify-center text-xs disabled:cursor-not-allowed disabled:opacity-50"
        >
          {exportingPdf ? t('chat.downloadingPdf') : t('chat.downloadPdf')}
        </button>
      </div>
    </>
  );

  if (inline) return <div className="shrink-0">{content}</div>;

  return <div className="nn-card shrink-0 p-4">{content}</div>;
}
