import { useTranslation } from 'react-i18next';
import GraphPanelShell from './GraphPanelShell.jsx';

export default function VerificationInbox({
  candidates,
  expanded,
  onToggleExpand,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <GraphPanelShell
      title={t('graph.verificationInbox')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
      className={className}
    >
      {!candidates?.length ? (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.verificationEmpty')}</p>
      ) : (
        <ul
          className={`space-y-2 ${
            expanded
              ? ''
              : 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-full overflow-y-auto'
          }`}
        >
          {candidates.map((candidate) => (
            <li
              key={candidate.id}
              className="rounded-lg border border-nn-border bg-nn-gray-light p-2.5 text-xs dark:border-slate-600 dark:bg-slate-800"
            >
              <p className="font-medium leading-snug text-gray-900 dark:text-slate-100">
                {candidate.name}{' '}
                <span className="font-normal text-nn-gray dark:text-slate-400">
                  ({t(`graph.nodeTypes.${candidate.type}`, { defaultValue: candidate.type })})
                </span>
              </p>
              <p className="mt-1 text-nn-gray dark:text-slate-400">
                {t('graph.confidence')}: {Math.round(candidate.confidence * 100)}%
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-nn-blue px-2.5 py-1 text-[11px] font-medium text-white hover:bg-nn-blue-dark"
                >
                  {t('graph.approve')}
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-nn-border bg-white px-2.5 py-1 text-[11px] font-medium text-nn-gray hover:bg-nn-gray-light dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {t('graph.reject')}
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-nn-border bg-white px-2.5 py-1 text-[11px] font-medium text-nn-gray hover:bg-nn-gray-light dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {t('graph.edit')}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </GraphPanelShell>
  );
}
