import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import SourceDocumentPanel from './SourceDocumentPanel.jsx';
import SourceLockedPanel from './SourceLockedPanel.jsx';

export default function SourceDocumentModal({ open, source, locked = false, onClose }) {
  const { t } = useTranslation();

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open || !source) return null;

  const isLocked = locked || source.locked || source.accessDenied;

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-center p-3 sm:items-center sm:p-6">
      <button
        type="button"
        aria-label={t('source.close')}
        className="absolute inset-0 bg-black/45"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 flex h-[min(94vh,900px)] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-nn-border bg-nn-gray-light shadow-xl dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-nn-border bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="text-sm font-semibold text-gray-900 dark:text-slate-100">{t('source.title')}</p>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-xs text-nn-gray hover:bg-nn-gray-light dark:text-slate-400 dark:hover:bg-slate-800"
          >
            {t('source.close')}
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          {isLocked ? <SourceLockedPanel sourceId={source.id} /> : <SourceDocumentPanel source={source} />}
        </div>
      </div>
    </div>
  );
}
