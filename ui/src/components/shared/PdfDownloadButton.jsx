import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export default function PdfDownloadButton({ onExport, disabled = false, className = '' }) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (!onExport || loading) return;
    setLoading(true);
    try {
      await onExport();
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      disabled={disabled || loading}
      onClick={handleClick}
      className={`shrink-0 rounded-lg border border-nn-border bg-white px-3 py-1.5 text-xs font-medium text-nn-blue transition-colors hover:bg-nn-blue-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-sky-300 dark:hover:bg-slate-800 ${className}`}
    >
      {loading ? t('common.downloadingPdf') : t('common.downloadPdf')}
    </button>
  );
}
