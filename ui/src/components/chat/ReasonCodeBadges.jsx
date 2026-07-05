import { useTranslation } from 'react-i18next';

export default function ReasonCodeBadges({ reasonCodes }) {
  const { t } = useTranslation();

  if (!reasonCodes?.length) return null;

  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {reasonCodes.map((code) => (
        <span
          key={code}
          className="rounded border border-amber-300/80 bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-amber-800 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
          title={t(`chat.answer.reasonCodes.${code}`, { defaultValue: code })}
        >
          {t(`chat.answer.reasonCodes.${code}`, { defaultValue: code })}
        </span>
      ))}
    </div>
  );
}
