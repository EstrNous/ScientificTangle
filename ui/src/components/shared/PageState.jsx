export function EmptyState({ title, message, action, className = '' }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 px-4 py-10 text-center ${className}`}
    >
      {title && (
        <p className="text-sm font-medium text-gray-900 dark:text-slate-100">{title}</p>
      )}
      {message && <p className="max-w-md text-sm text-nn-gray dark:text-slate-400">{message}</p>}
      {action}
    </div>
  );
}

export function ErrorBanner({ message, onRetry, retryLabel, className = '' }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200 ${className}`}
    >
      <span className="min-w-0 flex-1 break-words">{message}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium hover:bg-red-100 dark:border-red-800 dark:hover:bg-red-900"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export function DegradedBanner({ message, className = '' }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className={`rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100 ${className}`}
    >
      {message}
    </div>
  );
}
