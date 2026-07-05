import { useTranslation } from 'react-i18next';

const STATUS_STYLES = {
  pending: 'border-nn-border bg-white text-nn-gray dark:border-slate-600 dark:bg-slate-900 dark:text-slate-400',
  active: 'border-nn-blue bg-nn-blue-light text-nn-blue dark:border-sky-500 dark:bg-sky-950/40 dark:text-sky-300',
  done: 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200',
  failed: 'border-red-300 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200',
};

export default function UploadStageStepper({ stages = [] }) {
  const { t } = useTranslation();

  if (!stages.length) return null;

  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('upload.stagesTitle')}
      </p>
      <ol className="space-y-2">
        {stages.map((stage, index) => (
          <li
            key={`${stage.id}-${index}`}
            className={`rounded-lg border px-3 py-2 text-xs ${STATUS_STYLES[stage.status] ?? STATUS_STYLES.pending}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{stage.label}</span>
              <span className="uppercase tracking-wide">
                {t(`upload.stageStatuses.${stage.status}`, { defaultValue: stage.status })}
              </span>
            </div>
            {stage.warnings?.length > 0 && (
              <ul className="mt-2 space-y-1 text-[11px] text-amber-800 dark:text-amber-200">
                {stage.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
