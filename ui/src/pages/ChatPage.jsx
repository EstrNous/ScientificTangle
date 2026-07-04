import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ChatSidebar, ChatWindow, ChatInput } from '../components/chat/index.js';
import { ensureAuth } from '../api/auth.js';
import {
  createChatSession,
  deleteChatSession,
  fetchChatMessages,
  fetchChatSessions,
} from '../api/chat.js';
import { useChatAnswerFlow } from '../hooks/useChatAnswerFlow.js';

function sessionTitleFromText(text) {
  const trimmed = text.trim();
  if (!trimmed) return 'Новый запрос';
  return trimmed.length > 64 ? `${trimmed.slice(0, 61)}…` : trimmed;
}

function getApiErrorMessage(error, fallback) {
  return error?.response?.data?.message ?? error?.message ?? fallback;
}

export default function ChatPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const {
    phase,
    retrievalTrace,
    streamingDraft,
    streamingComplete,
    mode,
    isActive,
    streamingUxEnabled,
    sendAnswerQuery,
  } = useChatAnswerFlow();

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        await ensureAuth();
        const nextSessions = await fetchChatSessions();
        if (cancelled) return;
        setSessions(nextSessions);
        setActiveId(nextSessions[0]?.id ?? null);
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError, 'chat_load_failed'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return undefined;
    }

    let cancelled = false;
    fetchChatMessages(activeId)
      .then((items) => {
        if (!cancelled) setMessages(items);
      })
      .catch((loadError) => {
        if (!cancelled) setError(getApiErrorMessage(loadError, 'chat_messages_failed'));
      });

    return () => {
      cancelled = true;
    };
  }, [activeId]);

  if (loading) return <Loader />;

  const handleSend = async ({ text, files }) => {
    if (isActive || !text.trim()) return;

    setError(null);

    const attachments = files.map((f) => f.name);
    const optimisticUser = {
      id: `local-${Date.now()}`,
      role: 'user',
      content: text,
      attachments,
    };

    try {
      let sessionId = activeId;
      if (!sessionId) {
        const created = await createChatSession(sessionTitleFromText(text));
        sessionId = created.id;
        setSessions((prev) => [created, ...prev]);
        setActiveId(sessionId);
      }

      setMessages((prev) => [...prev, optimisticUser]);
      const reply = await sendAnswerQuery({ sessionId, text, files });
      setMessages((prev) => [...prev.filter((m) => m.id !== optimisticUser.id), optimisticUser, reply]);
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId
            ? { ...session, title: session.title || sessionTitleFromText(text) }
            : session,
        ),
      );
    } catch (sendError) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setError(getApiErrorMessage(sendError, 'chat_send_failed'));
    }
  };

  const handleDeleteSession = async (id) => {
    setError(null);
    try {
      await deleteChatSession(id);
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (activeId === id) {
          const nextActive = next[0]?.id ?? null;
          setActiveId(nextActive);
          if (!nextActive) setMessages([]);
        }
        return next;
      });
    } catch (deleteError) {
      setError(getApiErrorMessage(deleteError, 'chat_delete_failed'));
    }
  };

  const activeSession = sessions.find((s) => s.id === activeId);

  return (
    <PageShell>
      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {t('chat.backendError', { message: error })}
        </div>
      )}
      <div className="flex h-full min-h-0 flex-col lg:flex-row">
        <div className="mb-2 flex shrink-0 items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={() => setSidebarOpen((open) => !open)}
            className="rounded-lg border border-nn-border px-3 py-1.5 text-sm text-gray-900 transition-colors hover:bg-nn-gray-light dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
            aria-expanded={sidebarOpen}
          >
            {sidebarOpen ? t('chat.hideHistory') : t('chat.showHistory')}
          </button>
        </div>
        <ChatSidebar
          className={sidebarOpen ? 'flex' : 'hidden lg:flex'}
          sessions={sessions}
          activeId={activeId}
          onSelect={(id) => {
            setActiveId(id);
            setSidebarOpen(false);
          }}
          onDelete={handleDeleteSession}
          sessionId={activeId}
          sessionTitle={activeSession?.title}
          messages={messages}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:pl-4">
          <ChatWindow
            messages={messages}
            retrievalTrace={retrievalTrace}
            answerPhase={phase}
            answerMode={mode}
            streamingDraft={streamingDraft}
            streamingComplete={streamingComplete}
            streamingUxEnabled={streamingUxEnabled}
          />
          <ChatInput onSend={handleSend} disabled={isActive} />
        </div>
      </div>
    </PageShell>
  );
}
