import { useTranslation } from 'react-i18next';

function StepIcon({ status }) {
  if (status === 'done') {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-nn-blue text-xs text-white">
        ✓
      </span>
    );
  }
  if (status === 'active') {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-nn-blue border-t-transparent" />
      </span>
    );
  }
  return <span className="h-5 w-5 shrink-0 rounded-full border border-nn-border dark:border-slate-600" />;
}

export default function RetrievalProgress({ trace }) {
  const { t } = useTranslation();
  if (!trace?.steps?.length) return null;

  return (
    <div className="mr-8 min-h-[8rem] rounded-xl border border-nn-blue/20 bg-nn-blue-light px-4 py-3 dark:border-slate-600 dark:bg-slate-800">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-nn-blue">
        {t('chat.retrievalTitle')}
      </p>
      <ul className="space-y-2">
        {trace.steps.map((step) => (
          <li
            key={step.id}
            className={`flex items-start gap-2 text-sm ${
              step.status === 'active'
                ? 'font-medium text-gray-900 dark:text-slate-100'
                : step.status === 'done'
                  ? 'text-nn-gray dark:text-slate-400'
                  : 'text-nn-gray/60 dark:text-slate-500'
            }`}
          >
            <StepIcon status={step.status} />
            <span>{step.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
