import { useTranslation } from 'react-i18next';

const RISK_STYLES = {
  high: 'bg-gray-100 text-gray-800 dark:bg-slate-800 dark:text-slate-200',
  medium: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  low: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
};

export default function GapConflictView({ contradictions }) {
  const { t } = useTranslation();

  if (!contradictions?.length) return null;

  return (
    <div className="nn-card flex flex-col gap-3 p-4">
      <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('lab.conflictsTitle')}
      </p>
      <ul className="space-y-3">
        {contradictions.map((item) => (
          <li
            key={item.id}
            className="rounded-xl border border-nn-border bg-white p-3 dark:border-slate-700 dark:bg-slate-900"
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{item.process}</p>
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  RISK_STYLES[item.risk] ?? RISK_STYLES.medium
                }`}
              >
                {t(`lab.risk.${item.risk}`, { defaultValue: item.risk })}
              </span>
            </div>

            <div className="grid gap-2 text-xs md:grid-cols-2">
              <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 dark:border-slate-600 dark:bg-slate-800">
                <p className="font-medium text-gray-900 dark:text-slate-100">{item.claim_a}</p>
                <p className="mt-1 text-nn-gray dark:text-slate-400">{item.condition_a}</p>
                <p className="mt-1 text-[11px] text-nn-blue">{item.source_a}</p>
              </div>
              <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 dark:border-slate-600 dark:bg-slate-800">
                <p className="font-medium text-gray-900 dark:text-slate-100">{item.claim_b}</p>
                <p className="mt-1 text-nn-gray dark:text-slate-400">{item.condition_b}</p>
                <p className="mt-1 text-[11px] text-nn-blue">{item.source_b}</p>
              </div>
            </div>

            <p className="mt-2 text-[11px] text-nn-gray dark:text-slate-400">{t('lab.conflictNote')}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
