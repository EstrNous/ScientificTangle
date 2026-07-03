import { useTranslation } from 'react-i18next';

function HighlightedText({ text, highlight }) {
  if (!highlight || !text.includes(highlight)) {
    return <span>{text}</span>;
  }

  const [before, after] = text.split(highlight);
  return (
    <span>
      {before}
      <mark className="rounded bg-amber-200/80 px-0.5 text-gray-900 dark:bg-amber-500/30 dark:text-amber-100">
        {highlight}
      </mark>
      {after}
    </span>
  );
}

export default function SourceViewer({ span }) {
  const { t } = useTranslation();

  if (!span) {
    return (
      <div className="nn-card flex h-full min-h-0 items-center justify-center p-4 text-sm text-nn-gray dark:text-slate-400">
        {t('admin.sourceEmpty')}
      </div>
    );
  }

  return (
    <div className="nn-card flex h-full min-h-0 flex-col overflow-auto p-4">
      <p className="mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('admin.sourceTitle')}
      </p>
      <p className="shrink-0 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {span.title}
      </p>
      <p className="mt-1 shrink-0 text-xs text-nn-gray dark:text-slate-400">
        {t('admin.sourceMeta', { page: span.page, section: span.section })}
      </p>
      <div className="mt-3 rounded-lg border border-nn-border bg-nn-gray-light p-3 text-sm leading-relaxed text-gray-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200">
        <HighlightedText text={span.raw_text} highlight={span.highlight} />
      </div>
    </div>
  );
}
