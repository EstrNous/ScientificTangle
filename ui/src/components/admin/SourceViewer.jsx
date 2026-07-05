import { useTranslation } from 'react-i18next';
import SourceDocumentPanel from '../shared/SourceDocumentPanel.jsx';

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
      <p className="mb-3 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('admin.sourceTitle')}
      </p>
      <SourceDocumentPanel source={span} compact />
    </div>
  );
}
