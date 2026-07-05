import { useTranslation } from 'react-i18next';
import Loader from '../shared/Loader.jsx';
import SourceDocumentPanel from '../shared/SourceDocumentPanel.jsx';
import SourceLockedPanel from '../shared/SourceLockedPanel.jsx';

export default function ReviewSourcePanel({ source, loading, locked, sourceId }) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="nn-card flex h-full min-h-[12rem] items-center justify-center p-4">
        <Loader />
      </div>
    );
  }

  if (locked) {
    return (
      <div className="nn-card h-full min-h-0 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('review.sourcePanelTitle')}
        </p>
        <SourceLockedPanel sourceId={sourceId} />
      </div>
    );
  }

  if (!source) {
    return (
      <div className="nn-card flex h-full min-h-[12rem] items-center justify-center p-4 text-sm text-nn-gray dark:text-slate-400">
        {t('review.sourceEmpty')}
      </div>
    );
  }

  return (
    <div className="nn-card flex h-full min-h-0 flex-col overflow-hidden p-4">
      <p className="mb-3 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('review.sourcePanelTitle')}
      </p>
      <div className="min-h-0 flex-1 overflow-auto">
        <SourceDocumentPanel source={source} compact />
      </div>
    </div>
  );
}
