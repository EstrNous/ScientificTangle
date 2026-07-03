import { forwardRef, useImperativeHandle, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { collectSourceRefs } from '../../utils/sourceRefs.js';
import { useSourceRefsPopover } from '../../hooks/useSourceRefsPopover.js';
import { captureElementImage, waitForPaint } from '../../utils/captureElement.js';
import SourceRefsPopover from '../shared/SourceRefsPopover.jsx';

function MetricBar({ label, value, compact, onClick }) {
  const pct = Math.round((value ?? 0) * 100);
  const content = (
    <>
      <div
        className={`mb-0.5 flex justify-between text-nn-gray dark:text-slate-400 ${compact ? 'text-[10px]' : 'text-[11px]'}`}
      >
        <span>{label}</span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <div className={`overflow-hidden rounded-full bg-nn-gray-light dark:bg-slate-800 ${compact ? 'h-1' : 'h-1.5'}`}>
        <div className="h-full rounded-full bg-nn-blue" style={{ width: `${pct}%` }} />
      </div>
    </>
  );

  if (!onClick) return <div>{content}</div>;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-md px-1 py-0.5 text-left transition-colors hover:bg-nn-blue-light/50 dark:hover:bg-slate-800/60"
    >
      {content}
    </button>
  );
}

function SummaryCard({ label, value, suffix = '', compact }) {
  return (
    <div className="rounded-lg border border-nn-border bg-nn-gray-light px-2.5 py-1.5 dark:border-slate-600 dark:bg-slate-800">
      <p
        className={`font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400 ${compact ? 'text-[9px] leading-tight' : 'text-[10px]'}`}
      >
        {label}
      </p>
      <p
        className={`font-bold tabular-nums text-gray-900 dark:text-slate-100 ${compact ? 'mt-px text-base leading-none' : 'mt-0.5 text-lg'}`}
      >
        {value}
        {suffix}
      </p>
    </div>
  );
}

const EvaluationDashboard = forwardRef(function EvaluationDashboard({ data, fill = false }, ref) {
  const { t } = useTranslation();
  const captureRef = useRef(null);
  const scrollRef = useRef(null);
  const { popover, openPopover, closePopover } = useSourceRefsPopover();

  useImperativeHandle(ref, () => ({
    async getExportImage() {
      const root = captureRef.current;
      const scrollEl = scrollRef.current;
      if (!root) return '';

      const rootOverflow = root.style.overflow;
      root.style.overflow = 'visible';

      let scrollOverflow;
      let scrollMaxHeight;
      let scrollFlex;
      if (scrollEl) {
        scrollOverflow = scrollEl.style.overflow;
        scrollMaxHeight = scrollEl.style.maxHeight;
        scrollFlex = scrollEl.style.flex;
        scrollEl.style.overflow = 'visible';
        scrollEl.style.maxHeight = 'none';
        scrollEl.style.flex = 'none';
      }

      await waitForPaint();
      const image = await captureElementImage(root, { fullContent: true });

      root.style.overflow = rootOverflow;
      if (scrollEl) {
        scrollEl.style.overflow = scrollOverflow;
        scrollEl.style.maxHeight = scrollMaxHeight;
        scrollEl.style.flex = scrollFlex;
      }

      return image;
    },
  }));

  if (!data?.questions?.length) return null;

  const summary = data.summary ?? {};

  const openQuestionSources = (event, question) => {
    const sources = collectSourceRefs(question, question.actual_sources);
    if (!sources.length) return;
    openPopover(event, {
      title: question.text,
      subtitle: t('strategic.sourcesLine', {
        actual: question.actual_sources,
        expected: question.expected_sources,
      }),
      sources,
    });
  };

  const openMetricSources = (event, question, metricKey, value) => {
    const sources = collectSourceRefs(question, Math.max(1, Math.round((value ?? 0) * 4)));
    if (!sources.length) return;
    openPopover(event, {
      title: question.text,
      subtitle: t(`strategic.evalMetrics.${metricKey}`),
      sources,
    });
  };

  return (
    <div
      ref={captureRef}
      className={`nn-card flex flex-col ${fill ? 'min-h-0 flex-1 gap-2 overflow-hidden p-3' : 'gap-4 p-4'}`}
    >
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('strategic.evaluationTitle')}
        </p>
        <p className="text-xs text-nn-gray dark:text-slate-400">
          {t('strategic.evaluationSubtitle', { count: data.questions.length })}
        </p>
      </div>

      <div className="grid shrink-0 grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        <SummaryCard
          label={t('strategic.evalMetrics.citation_coverage')}
          value={`${Math.round((summary.avg_citation_coverage ?? 0) * 100)}%`}
          compact={fill}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.numeric_correctness')}
          value={`${Math.round((summary.avg_numeric_correctness ?? 0) * 100)}%`}
          compact={fill}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.latency')}
          value={summary.avg_latency_ms ?? '—'}
          suffix={summary.avg_latency_ms ? ' ms' : ''}
          compact={fill}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.unsupported_rate')}
          value={`${Math.round((summary.unsupported_claim_rate ?? 0) * 100)}%`}
          compact={fill}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.entity_f1')}
          value={`${Math.round((summary.entity_linking_f1 ?? 0) * 100)}%`}
          compact={fill}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.recall_at_5')}
          value={`${Math.round((summary.evidence_recall_at_5 ?? 0) * 100)}%`}
          compact={fill}
        />
      </div>

      <div
        ref={scrollRef}
        className={`min-h-0 ${fill ? 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 flex-1 overflow-y-auto pr-0.5' : ''}`}
      >
        <div className={`grid gap-2 ${fill ? 'lg:grid-cols-2' : 'gap-3 lg:grid-cols-2'}`}>
          {data.questions.map((question) => {
            const statusKey = question.status === 'pass' ? 'pass' : 'warn';
            const statusClass =
              question.status === 'pass'
                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                : 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300';

            return (
              <article
                key={question.id}
                className={`rounded-xl border border-nn-border bg-white dark:border-slate-700 dark:bg-slate-900 ${fill ? 'p-2.5' : 'p-4'}`}
              >
                <div className={`flex items-start justify-between gap-2 ${fill ? 'mb-2' : 'mb-3'}`}>
                  <button
                    type="button"
                    onClick={(event) => openQuestionSources(event, question)}
                    className={`text-left font-medium text-gray-900 transition-colors hover:text-nn-blue dark:text-slate-100 dark:hover:text-sky-400 ${fill ? 'text-xs leading-snug' : 'text-sm'}`}
                  >
                    {question.text}
                  </button>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass}`}
                  >
                    {t(`strategic.status.${statusKey}`)}
                  </span>
                </div>

                <div
                  className={`grid grid-cols-2 gap-x-2 gap-y-1 text-nn-gray dark:text-slate-400 ${fill ? 'mb-2 text-[10px]' : 'mb-3 text-xs'}`}
                >
                  <button
                    type="button"
                    onClick={(event) => openQuestionSources(event, question)}
                    className="rounded-md px-1 py-0.5 text-left transition-colors hover:bg-nn-blue-light/50 dark:hover:bg-slate-800/60"
                  >
                    {t('strategic.sources')}:{' '}
                    <span className="font-medium text-gray-900 dark:text-slate-100">
                      {question.actual_sources}/{question.expected_sources}
                    </span>
                  </button>
                  <p>
                    {t('strategic.missingEvidence')}:{' '}
                    <span className="font-medium text-gray-900 dark:text-slate-100">
                      {question.missing_evidence}
                    </span>
                  </p>
                  <p>
                    {t('strategic.unsupportedClaims')}:{' '}
                    <span className="font-medium text-gray-900 dark:text-slate-100">
                      {question.unsupported_claims}
                    </span>
                  </p>
                  <p>
                    {t('strategic.latency')}:{' '}
                    <span className="font-medium text-gray-900 dark:text-slate-100">
                      {question.latency_ms} ms
                    </span>
                  </p>
                </div>

                <div className={fill ? 'space-y-1.5' : 'space-y-2'}>
                  <MetricBar
                    label={t('strategic.evalMetrics.citation_coverage')}
                    value={question.citation_coverage}
                    compact={fill}
                    onClick={(event) =>
                      openMetricSources(event, question, 'citation_coverage', question.citation_coverage)
                    }
                  />
                  <MetricBar
                    label={t('strategic.evalMetrics.numeric_correctness')}
                    value={question.numeric_correctness}
                    compact={fill}
                    onClick={(event) =>
                      openMetricSources(event, question, 'numeric_correctness', question.numeric_correctness)
                    }
                  />
                </div>
              </article>
            );
          })}
        </div>
      </div>
      <SourceRefsPopover state={popover} onClose={closePopover} />
    </div>
  );
});

export default EvaluationDashboard;
