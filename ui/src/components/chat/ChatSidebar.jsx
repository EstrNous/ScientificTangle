import { useTranslation } from 'react-i18next';
import ExportPanel from './ExportPanel.jsx';
import LocalGraph from '../graph/LocalGraph.jsx';

function DeleteIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

export default function ChatSidebar({
  sessions,
  activeId,
  onSelect,
  onDelete,
  sessionId,
  sessionTitle,
  messages,
  subgraph,
}) {
  const { t } = useTranslation();

  return (
    <aside className="flex w-72 shrink-0 flex-col gap-6 border-r border-nn-border pr-4 dark:border-slate-700">
      <div className="flex min-h-0 flex-1 flex-col">
        <p className="mb-3 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('chat.history')}
        </p>
        <div className="relative min-h-0 flex-1">
          <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-64 space-y-2 overflow-y-auto pr-1">
            {sessions.map((s) => (
              <li key={s.id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(s.id)}
                  className={`w-full rounded-xl border px-3 py-3 pr-9 text-left text-sm transition-colors ${
                    activeId === s.id
                      ? 'border-nn-blue bg-nn-blue-light text-nn-blue dark:bg-slate-800'
                      : 'border-nn-border bg-white text-gray-900 group-hover:border-nn-gray group-hover:bg-nn-gray-light dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:group-hover:border-slate-500 dark:group-hover:bg-slate-800'
                  }`}
                >
                  <span className="line-clamp-2 font-medium">{s.title}</span>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete?.(s.id);
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-nn-gray opacity-0 transition-opacity hover:bg-nn-gray-light hover:text-gray-900 group-hover:opacity-100 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100"
                  title={t('chat.deleteSession')}
                  aria-label={t('chat.deleteSession')}
                >
                  <DeleteIcon />
                </button>
              </li>
            ))}
          </ul>
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-white to-transparent dark:from-slate-900"
            aria-hidden
          />
        </div>
        <p className="mt-2 shrink-0 text-center text-[10px] text-nn-gray dark:text-slate-500">
          {t('chat.scrollHint')}
        </p>
      </div>

      <ExportPanel
        sessionId={sessionId}
        sessionTitle={sessionTitle}
        messages={messages}
        inline
      />

      {subgraph && <LocalGraph subgraph={subgraph} inline />}
    </aside>
  );
}
