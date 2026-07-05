import { useTranslation } from 'react-i18next';

const editButtonClassName =
  'rounded-lg border border-nn-border bg-white px-3 py-1.5 text-sm font-medium text-nn-blue transition-colors hover:bg-nn-blue-light dark:border-slate-600 dark:bg-slate-900 dark:hover:bg-slate-800';

export default function ProfileSection({
  title,
  summary,
  editing = false,
  editable = true,
  onEdit,
  onCancel,
  children,
  danger = false,
  className = '',
  compact = false,
}) {
  const { t } = useTranslation();
  const expanded = editable ? editing : true;

  return (
    <section
      className={`flex flex-col rounded-xl border ${
        compact ? 'p-4' : 'p-5'
      } ${
        danger
          ? 'border-red-200 bg-red-50/50 dark:border-red-900/50 dark:bg-red-950/20'
          : 'border-nn-border bg-white dark:border-slate-700 dark:bg-slate-900'
      } ${className}`}
    >
      <div className={`flex shrink-0 items-start justify-between gap-3 ${title || !compact ? 'mb-3' : 'mb-2'}`}>
        {title ? (
          <h3 className="text-sm font-semibold text-gray-900 dark:text-slate-100">{title}</h3>
        ) : (
          <span />
        )}
        {editable &&
          (!editing ? (
            <button type="button" onClick={onEdit} className={editButtonClassName}>
              {t('profile.edit')}
            </button>
          ) : (
            <button type="button" onClick={onCancel} className={editButtonClassName}>
              {t('profile.cancel')}
            </button>
          ))}
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">{expanded ? children : summary}</div>
      {danger && expanded && (
        <p className="mt-3 shrink-0 text-xs text-red-700 dark:text-red-300">{t('profile.dangerHint')}</p>
      )}
    </section>
  );
}
