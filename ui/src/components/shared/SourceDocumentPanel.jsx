import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getSourcePageContent, getSourcePageNumbers } from '../../api/mock/sourceCatalog.js';
import { downloadSourceDocumentPdf } from '../../utils/downloadSource.js';
import HighlightedText from './HighlightedText.jsx';

export default function SourceDocumentPanel({ source, compact = false }) {
  const { t } = useTranslation();
  const pageNumbers = useMemo(() => getSourcePageNumbers(source), [source]);
  const [currentPage, setCurrentPage] = useState(source?.page ?? 1);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setCurrentPage(source?.page ?? 1);
  }, [source?.id, source?.page]);

  if (!source) return null;

  const pageIndex = pageNumbers.indexOf(currentPage);
  const hasPrev = pageIndex > 0;
  const hasNext = pageIndex >= 0 && pageIndex < pageNumbers.length - 1;
  const { raw_text: rawText, highlight } = getSourcePageContent(source, currentPage);

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      await downloadSourceDocumentPdf(source);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className={`flex min-h-0 flex-col ${compact ? 'gap-2' : 'gap-3'}`}>
      <div className="flex shrink-0 flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{source.title}</p>
          <p className="mt-1 text-xs text-nn-gray dark:text-slate-400">
            {t('source.page', { page: currentPage })}
            {source.section ? ` · ${source.section}` : ''}
            {source.total_pages ? ` · ${t('source.totalPages', { count: source.total_pages })}` : ''}
          </p>
        </div>
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="shrink-0 rounded-lg border border-nn-border px-3 py-1.5 text-xs font-medium text-nn-blue hover:bg-nn-blue-light disabled:opacity-60 dark:border-slate-600 dark:text-sky-300 dark:hover:bg-slate-800"
        >
          {downloading ? t('source.downloading') : t('source.download')}
        </button>
      </div>

      {pageNumbers.length > 1 && (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!hasPrev}
            onClick={() => setCurrentPage(pageNumbers[pageIndex - 1])}
            className="rounded-md border border-nn-border px-2 py-1 text-[11px] text-gray-800 disabled:opacity-40 dark:border-slate-600 dark:text-slate-200"
          >
            {t('source.prevPage')}
          </button>
          <div className="flex flex-wrap gap-1">
            {pageNumbers.map((page) => (
              <button
                key={page}
                type="button"
                onClick={() => setCurrentPage(page)}
                className={`rounded-md px-2 py-1 text-[11px] font-medium ${
                  page === currentPage
                    ? 'bg-nn-blue text-white dark:bg-sky-600'
                    : 'border border-nn-border text-gray-800 dark:border-slate-600 dark:text-slate-200'
                }`}
              >
                {page}
              </button>
            ))}
          </div>
          <button
            type="button"
            disabled={!hasNext}
            onClick={() => setCurrentPage(pageNumbers[pageIndex + 1])}
            className="rounded-md border border-nn-border px-2 py-1 text-[11px] text-gray-800 disabled:opacity-40 dark:border-slate-600 dark:text-slate-200"
          >
            {t('source.nextPage')}
          </button>
        </div>
      )}

      <div
        className={`min-h-0 flex-1 overflow-auto rounded-lg border border-nn-border bg-nn-gray-light text-sm leading-relaxed text-gray-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 ${
          compact ? 'p-3' : 'p-4'
        }`}
      >
        {rawText ? (
          <HighlightedText text={rawText} highlight={highlight} />
        ) : (
          <p className="text-nn-gray dark:text-slate-400">{t('source.pageEmpty')}</p>
        )}
      </div>
    </div>
  );
}
