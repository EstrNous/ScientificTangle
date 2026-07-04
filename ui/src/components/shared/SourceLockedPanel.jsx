import { useTranslation } from 'react-i18next';

export default function SourceLockedPanel({ sourceId }) {
  const { t } = useTranslation();

  return (
    <div className="flex h-full min-h-[12rem] flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50/70 p-6 text-center dark:border-red-900/60 dark:bg-red-950/30">
      <p className="text-sm font-semibold text-red-900 dark:text-red-200">{t('source.lockedTitle')}</p>
      <p className="max-w-md text-xs text-red-800/90 dark:text-red-200/80">{t('source.lockedHint')}</p>
      {sourceId && (
        <p className="font-mono text-[11px] text-red-700/80 dark:text-red-300/70">{sourceId}</p>
      )}
    </div>
  );
}
