import { useEffect, useState } from 'react';
import { apiGet } from '../../api/client.js';
import { useNotificationStore } from '../../stores/notificationStore.js';

function BellIcon() {
  return (
    <svg className="h-5 w-5 text-nn-blue" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path d="M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4.5A1.5 1.5 0 0 0 12 3a1.5 1.5 0 0 0-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
    </svg>
  );
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const items = useNotificationStore((s) => s.items);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const setItems = useNotificationStore((s) => s.setItems);
  const markAllRead = useNotificationStore((s) => s.markAllRead);

  useEffect(() => {
    apiGet('/notifications').then(setItems).catch(() => {});
  }, [setItems]);

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Уведомления"
        onClick={() => {
          setOpen(!open);
          if (!open) markAllRead();
        }}
        className="relative rounded-lg border border-nn-border p-2 hover:bg-nn-gray-light dark:border-slate-600 dark:hover:bg-slate-800"
      >
        <BellIcon />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-xs text-white">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 max-h-64 w-72 overflow-auto rounded-xl border border-nn-border bg-white shadow-card dark:border-slate-700 dark:bg-slate-900">
          {items.length === 0 ? (
            <p className="p-3 text-sm text-nn-gray dark:text-slate-400">Нет уведомлений</p>
          ) : (
            items.map((n) => (
              <div
                key={n.id}
                className="border-b border-nn-border p-3 text-sm last:border-0 dark:border-slate-700"
              >
                <p className="font-medium text-gray-900 dark:text-slate-100">{n.title}</p>
                <p className="mt-1 text-xs text-nn-gray dark:text-slate-400">{n.reason}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
