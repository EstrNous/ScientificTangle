import { useTranslation } from 'react-i18next';

function MetricBar({ label, value }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div>
      <div className="mb-1 flex justify-between text-[11px] text-nn-gray dark:text-slate-400">
        <span>{label}</span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-nn-gray-light dark:bg-slate-800">
        <div className="h-full rounded-full bg-nn-blue" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SummaryCard({ label, value, suffix = '' }) {
  return (
    <div className="rounded-lg border border-nn-border bg-nn-gray-light px-3 py-2 dark:border-slate-600 dark:bg-slate-800">
      <p className="text-[10px] font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {label}
      </p>
      <p className="mt-0.5 text-lg font-bold tabular-nums text-gray-900 dark:text-slate-100">
        {value}
        {suffix}
      </p>
    </div>
  );
}

export default function EvaluationDashboard({ data }) {
  const { t } = useTranslation();

  if (!data?.questions?.length) return null;

  const summary = data.summary ?? {};

  return (
    <div className="nn-card flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
          {t('strategic.evaluationTitle')}
        </p>
        <p className="text-xs text-nn-gray dark:text-slate-400">
          {t('strategic.evaluationSubtitle', { count: data.questions.length })}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        <SummaryCard
          label={t('strategic.evalMetrics.citation_coverage')}
          value={`${Math.round((summary.avg_citation_coverage ?? 0) * 100)}%`}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.numeric_correctness')}
          value={`${Math.round((summary.avg_numeric_correctness ?? 0) * 100)}%`}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.latency')}
          value={summary.avg_latency_ms ?? '—'}
          suffix={summary.avg_latency_ms ? ' ms' : ''}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.unsupported_rate')}
          value={`${Math.round((summary.unsupported_claim_rate ?? 0) * 100)}%`}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.entity_f1')}
          value={`${Math.round((summary.entity_linking_f1 ?? 0) * 100)}%`}
        />
        <SummaryCard
          label={t('strategic.evalMetrics.recall_at_5')}
          value={`${Math.round((summary.evidence_recall_at_5 ?? 0) * 100)}%`}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {data.questions.map((question) => {
          const statusKey = question.status === 'pass' ? 'pass' : 'warn';
          const statusClass =
            question.status === 'pass'
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
              : 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300';

          return (
            <article
              key={question.id}
              className="rounded-xl border border-nn-border bg-white p-4 dark:border-slate-700 dark:bg-slate-900"
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{question.text}</p>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${statusClass}`}
                >
                  {t(`strategic.status.${statusKey}`)}
                </span>
              </div>

              <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-nn-gray dark:text-slate-400">
                <p>
                  {t('strategic.sources')}:{' '}
                  <span className="font-medium text-gray-900 dark:text-slate-100">
                    {question.actual_sources}/{question.expected_sources}
                  </span>
                </p>
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

              <div className="space-y-2">
                <MetricBar
                  label={t('strategic.evalMetrics.citation_coverage')}
                  value={question.citation_coverage}
                />
                <MetricBar
                  label={t('strategic.evalMetrics.numeric_correctness')}
                  value={question.numeric_correctness}
                />
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
