import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';

export default function UploadPage() {
  const { t } = useTranslation();

  return (
    <PageShell>
      <div className="flex h-full items-center justify-center text-sm text-nn-gray dark:text-slate-400">
        {t('common.placeholder')}
      </div>
    </PageShell>
  );
}
