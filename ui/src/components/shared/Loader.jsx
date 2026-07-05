import { useTranslation } from 'react-i18next';

export default function Loader() {
  const { t } = useTranslation();
  return (
    <div className="flex h-full items-center justify-center text-sm text-nn-gray dark:text-slate-400">
      <span className="animate-pulse">{t('common.loading')}</span>
    </div>
  );
}
