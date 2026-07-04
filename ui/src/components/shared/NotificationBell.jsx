import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../api/notifications.js';
import { useMock } from '../../api/client.js';
import { useNotificationStore } from '../../stores/notificationStore.js';
import { useSourceDocument } from '../../context/SourceDocumentContext.jsx';
import { isLiveNotificationsEnabled } from '../../utils/uiFeatureFlags.js';
import {
  notificationTitleKey,
  resolveNotificationTarget,
} from '../../utils/notificationNavigation.js';

const POLL_INTERVAL_MS = 30000;

function BellIcon() {
  return (
    <svg className="h-5 w-5 text-nn-blue" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path d="M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4.5A1.5 1.5 0 0 0 12 3a1.5 1.5 0 0 0-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
    </svg>
  );
}

function formatRelativeTime(value, locale) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return locale === 'ru' ? 'только что' : 'just now';
  if (minutes < 60) {
    return locale === 'ru' ? `${minutes} мин назад` : `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return locale === 'ru' ? `${hours} ч назад` : `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return locale === 'ru' ? `${days} дн назад` : `${days}d ago`;
}

function resolveItemTitle(item, t) {
  const key = notificationTitleKey(item.type);
  const localized = key ? t(key, { defaultValue: '' }) : '';
  if (localized) {
    return localized;
  }
  return item.title;
}

export default function NotificationBell() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { openSource } = useSourceDocument();
  const panelRef = useRef(null);
  const lastPolledRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [toast, setToast] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const items = useNotificationStore((s) => s.items);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const loading = useNotificationStore((s) => s.loading);
  const setItems = useNotificationStore((s) => s.setItems);
  const mergeItems = useNotificationStore((s) => s.mergeItems);
  const setLoading = useNotificationStore((s) => s.setLoading);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);

  const pollingEnabled = !useMock || isLiveNotificationsEnabled();

  const loadNotifications = async ({ since, resetError = true } = {}) => {
    if (resetError) setLoadError(null);
    const data = await fetchNotifications(since ? { since } : {});
    const list = Array.isArray(data) ? data : data?.items ?? [];
    if (since) {
      mergeItems(list);
    } else {
      setItems(list);
    }
    lastPolledRef.current = new Date().toISOString();
    return list;
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    loadNotifications()
      .catch(() => {
        if (active) {
          setItems([]);
          setLoadError('notifications_load_failed');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [setItems, setLoading]);

  useEffect(() => {
    if (!pollingEnabled) return undefined;
    const poll = async () => {
      try {
        const since = lastPolledRef.current ?? new Date(Date.now() - POLL_INTERVAL_MS).toISOString();
        const incoming = await fetchNotifications({ since });
        const list = Array.isArray(incoming) ? incoming : incoming?.items ?? [];
        if (!list.length) return;
        const unreadIncoming = list.filter((item) => !item.read);
        mergeItems(list);
        lastPolledRef.current = new Date().toISOString();
        if (unreadIncoming.length > 0) {
          const latest = unreadIncoming[0];
          setToast({
            id: latest.id,
            title: resolveItemTitle(latest, t),
          });
        }
      } catch {
      }
    };
    const timer = window.setInterval(poll, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [mergeItems, pollingEnabled, t]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!open) return undefined;
    const handlePointerDown = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [open]);

  const handleToggle = () => setOpen((value) => !value);

  const handleRefresh = async () => {
    setRefreshing(true);
    setLoadError(null);
    try {
      await loadNotifications();
    } catch {
      setLoadError('notifications_load_failed');
    } finally {
      setRefreshing(false);
    }
  };

  const handleMarkAll = async () => {
    markAllRead();
    try {
      await markAllNotificationsRead();
    } catch {
    }
  };

  const handleItemClick = async (item) => {
    if (!item.read) {
      markRead(item.id);
      try {
        await markNotificationRead(item.id);
      } catch {
      }
    }
    const target = resolveNotificationTarget(item);
    if (target.kind === 'source') {
      setOpen(false);
      await openSource(target.ref);
      return;
    }
    if (target.kind === 'navigate') {
      setOpen(false);
      navigate(target.path, target.state ? { state: target.state } : undefined);
    }
  };

  return (
    <div className="relative" ref={panelRef}>
      {toast && (
        <div
          role="status"
          className="absolute right-0 top-full z-50 mt-2 w-72 rounded-lg border border-nn-border bg-white px-3 py-2 shadow-card dark:border-slate-700 dark:bg-slate-900"
        >
          <p className="text-xs font-medium text-nn-blue dark:text-sky-300">
            {t('notifications.newTitle')}
          </p>
          <p className="mt-1 text-sm text-gray-900 dark:text-slate-100">{toast.title}</p>
        </div>
      )}
      <button
        type="button"
        aria-label={t('notifications.bell')}
        aria-expanded={open}
        onClick={handleToggle}
        className="relative rounded-lg border border-nn-border p-2 hover:bg-nn-gray-light dark:border-slate-600 dark:hover:bg-slate-800"
      >
        <BellIcon />
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-xs text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-nn-border bg-white shadow-card dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center justify-between border-b border-nn-border px-4 py-3 dark:border-slate-700">
            <span className="text-sm font-semibold text-gray-900 dark:text-slate-100">
              {t('notifications.title')}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRefresh}
                disabled={refreshing}
                className="text-xs font-medium text-nn-blue hover:underline disabled:cursor-not-allowed disabled:opacity-50"
              >
                {refreshing ? t('notifications.refreshing') : t('notifications.refresh')}
              </button>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAll}
                  className="text-xs font-medium text-nn-blue hover:underline"
                >
                  {t('notifications.markAllRead')}
                </button>
              )}
            </div>
          </div>
          <div className="max-h-80 overflow-auto">
            {loadError ? (
              <p className="p-4 text-sm text-red-600 dark:text-red-400">
                {t(`notifications.errors.${loadError}`, { defaultValue: loadError })}
              </p>
            ) : loading && items.length === 0 ? (
              <p className="p-4 text-sm text-nn-gray dark:text-slate-400">
                {t('notifications.loading')}
              </p>
            ) : items.length === 0 ? (
              <p className="p-4 text-sm text-nn-gray dark:text-slate-400">
                {t('notifications.empty')}
              </p>
            ) : (
              items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleItemClick(item)}
                  className={`flex w-full gap-3 border-b border-nn-border px-4 py-3 text-left last:border-0 dark:border-slate-700 ${
                    item.read
                      ? 'bg-white dark:bg-slate-900'
                      : 'bg-nn-blue-light/40 dark:bg-slate-800/80'
                  }`}
                >
                  {!item.read && (
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-nn-blue" aria-hidden />
                  )}
                  <span className={`min-w-0 flex-1 ${item.read ? 'pl-5' : ''}`}>
                    <span className="block text-sm font-medium text-gray-900 dark:text-slate-100">
                      {resolveItemTitle(item, t)}
                    </span>
                    <span className="mt-1 block text-xs text-nn-gray dark:text-slate-400">
                      {item.reason}
                    </span>
                    <span className="mt-1 block text-xs text-nn-gray/80 dark:text-slate-500">
                      {formatRelativeTime(item.createdAt ?? item.created_at, i18n.language)}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
