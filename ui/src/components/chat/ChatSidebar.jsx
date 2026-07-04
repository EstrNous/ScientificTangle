import { useTranslation } from 'react-i18next';
import ExportPanel from './ExportPanel.jsx';

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

function PlusIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

export default function ChatSidebar({
  sessions,
  activeId,
  onSelect,
  onDelete,
  onNewChat,
  creatingChat = false,
  sessionId,
  sessionTitle,
  messages,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <aside
      className={`w-full shrink-0 flex-col gap-4 border-b border-nn-border pb-4 lg:flex lg:w-72 lg:gap-6 lg:border-b-0 lg:border-r lg:pr-4 dark:border-slate-700 ${className}`}
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="mb-3 flex shrink-0 items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
            {t('chat.history')}
          </p>
          <button
            type="button"
            onClick={onNewChat}
            disabled={creatingChat || !onNewChat}
            className="inline-flex items-center gap-1.5 rounded-lg border border-nn-border px-2.5 py-1 text-xs font-medium text-gray-900 transition-colors hover:bg-nn-gray-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            <PlusIcon />
            {t('chat.newChat')}
          </button>
        </div>
        <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
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
      </div>

      <ExportPanel
        sessionId={sessionId}
        sessionTitle={sessionTitle}
        messages={messages}
        inline
      />
    </aside>
  );
}
