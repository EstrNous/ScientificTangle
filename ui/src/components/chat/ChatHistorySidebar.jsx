export default function ChatHistorySidebar({ sessions, activeId, onSelect }) {
  return (
    <div className="flex w-64 shrink-0 flex-col border-r border-nn-border pr-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-nn-gray">
        История
      </p>
      <ul className="space-y-2 overflow-auto">
        {sessions.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              onClick={() => onSelect(s.id)}
              className={`w-full rounded-xl border px-3 py-3 text-left text-sm transition-colors ${
                activeId === s.id
                  ? 'border-nn-blue bg-nn-blue-light text-nn-blue'
                  : 'border-nn-border bg-white text-gray-900 hover:border-nn-blue/40'
              }`}
            >
              <span className="line-clamp-2 font-medium">{s.title}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
