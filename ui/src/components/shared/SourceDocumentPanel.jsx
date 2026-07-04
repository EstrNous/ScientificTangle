import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getDocumentViewPages } from '../../api/sourceResolver/index.js';
import { downloadSourceDocumentPdf } from '../../utils/downloadSource.js';
import HighlightedText from './HighlightedText.jsx';

export default function SourceDocumentPanel({ source, compact = false }) {
  const { t } = useTranslation();
  const citedRef = useRef(null);
  const [downloading, setDownloading] = useState(false);
  const pages = useMemo(() => getDocumentViewPages(source), [source]);

  useEffect(() => {
    if (!citedRef.current) return undefined;
    const timer = window.setTimeout(() => {
      citedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [source?.id, source?.page]);

  if (!source) return null;

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
    <div className={`flex min-h-0 flex-col ${compact ? 'gap-3' : 'gap-4'}`}>
      <div className="flex shrink-0 flex-wrap items-start justify-between gap-3 border-b border-nn-border pb-3 dark:border-slate-700">
        <div className="min-w-0">
          <p className="text-base font-semibold text-gray-900 dark:text-slate-100">{source.title}</p>
          <p className="mt-1 text-xs text-nn-gray dark:text-slate-400">
            {source.file_name && source.file_name !== source.title ? `${source.file_name} · ` : ''}
            {source.total_pages
              ? t('source.totalPages', { count: source.total_pages })
              : t('source.pageCount', { count: pages.length })}
            {source.section ? ` · ${source.section}` : ''}
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

      <article
        className={`mx-auto w-full rounded-xl border border-nn-border bg-white shadow-sm dark:border-slate-600 dark:bg-slate-950 ${
          compact ? 'px-4 py-5' : 'px-6 py-8 sm:px-10 sm:py-10'
        }`}
      >
        {pages.map((page, index) => (
          <section
            key={page.page}
            ref={page.isCited ? citedRef : null}
            className={`${index > 0 ? 'mt-8 border-t border-dashed border-nn-border pt-8 dark:border-slate-700' : ''} ${
              page.isCited
                ? 'rounded-lg border border-amber-300/80 bg-amber-50/60 p-4 dark:border-amber-500/40 dark:bg-amber-500/10'
                : ''
            }`}
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
                {t('source.pageLabel', { page: page.page })}
              </span>
              {page.isCited && (
                <span className="rounded-full bg-amber-200/80 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-900 dark:bg-amber-500/30 dark:text-amber-100">
                  {t('source.citedFragment')}
                </span>
              )}
              {page.section && (
                <span className="text-[11px] text-nn-blue dark:text-sky-400">{page.section}</span>
              )}
            </div>
            {page.raw_text ? (
              <p className="whitespace-pre-wrap text-sm leading-7 text-gray-800 dark:text-slate-200">
                <HighlightedText text={page.raw_text} highlight={page.highlight} />
              </p>
            ) : (
              <p className="text-sm text-nn-gray dark:text-slate-400">{t('source.pageEmpty')}</p>
            )}
          </section>
        ))}
      </article>
    </div>
  );
}
