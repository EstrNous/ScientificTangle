import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ErrorBanner } from '../components/shared/PageState.jsx';
import { ChatSidebar, ChatWindow, ChatInput } from '../components/chat/index.js';
import { ensureAuth } from '../api/auth.js';
import { getApiErrorMessage } from '../api/errors.js';
import {
  createChatSession,
  deleteChatSession,
  fetchChatMessages,
  fetchChatSessions,
} from '../api/chat.js';
import { useChatAnswerFlow } from '../hooks/useChatAnswerFlow.js';
import {
  findReusableEmptyDraftSession,
  sessionTitleFromText,
} from '../utils/chatSession.js';

export default function ChatPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [creatingChat, setCreatingChat] = useState(false);
  const chatInputRef = useRef(null);
  const {
    phase,
    retrievalTrace,
    streamingDraft,
    streamingComplete,
    mode,
    failReason,
    isActive,
    streamingUxEnabled,
    sendAnswerQuery,
    reset,
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

  const defaultSessionTitle = t('chat.defaultSessionTitle');
  const isMac =
    typeof navigator !== 'undefined' && /Mac|iPhone|iPod|iPad/.test(navigator.platform);
  const newChatShortcut = t('chat.newChatShortcut', {
    shortcut: isMac ? '⌘N' : 'Ctrl+N',
  });
  const newChatLabel = creatingChat ? t('chat.creatingChat') : t('chat.newChat');
  const newChatDisabled = creatingChat || isActive;

  const focusChatInput = useCallback(() => {
    requestAnimationFrame(() => {
      chatInputRef.current?.focus();
    });
  }, []);

  const handleNewChat = useCallback(async () => {
    if (creatingChat || isActive) return;

    setError(null);

    const reusableDraft = findReusableEmptyDraftSession(
      sessions,
      activeId,
      messages,
      defaultSessionTitle,
    );
    if (reusableDraft) {
      reset();
      if (reusableDraft.id !== activeId) {
        setActiveId(reusableDraft.id);
      }
      setSidebarOpen(false);
      focusChatInput();
      return;
    }

    setCreatingChat(true);
    try {
      const created = await createChatSession(defaultSessionTitle);
      reset();
      setSessions((prev) => [created, ...prev]);
      setActiveId(created.id);
      setMessages([]);
      setSidebarOpen(false);
      focusChatInput();
    } catch (createError) {
      setError(getApiErrorMessage(createError, 'chat_create_failed'));
    } finally {
      setCreatingChat(false);
    }
  }, [
    activeId,
    creatingChat,
    defaultSessionTitle,
    focusChatInput,
    isActive,
    messages,
    reset,
    sessions,
  ]);

  useEffect(() => {
    if (loading) return undefined;
    const onKeyDown = (event) => {
      if (event.key !== 'n' && event.key !== 'N') return;
      if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return;
      event.preventDefault();
      handleNewChat();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleNewChat, loading]);

  if (loading) return <Loader />;

  const handleSelectSession = (id) => {
    if (id !== activeId) {
      reset();
    }
    setActiveId(id);
    setSidebarOpen(false);
  };

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

    let sessionId = activeId;

    try {
      if (!sessionId) {
        const reusableDraft = findReusableEmptyDraftSession(
          sessions,
          activeId,
          messages,
          defaultSessionTitle,
        );
        if (reusableDraft) {
          sessionId = reusableDraft.id;
          setActiveId(sessionId);
        } else {
          const created = await createChatSession(sessionTitleFromText(text, defaultSessionTitle));
          sessionId = created.id;
          setSessions((prev) => [created, ...prev]);
          setActiveId(sessionId);
        }
      }

      setMessages((prev) => [...prev, optimisticUser]);
      const reply = await sendAnswerQuery({ sessionId, text, files });
      setMessages((prev) => [...prev.filter((m) => m.id !== optimisticUser.id), optimisticUser, reply]);
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId
            ? { ...session, title: session.title || sessionTitleFromText(text, defaultSessionTitle) }
            : session,
        ),
      );
    } catch (sendError) {
      if (sessionId) {
        try {
          const persisted = await fetchChatMessages(sessionId);
          setMessages(persisted);
        } catch {
          setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
        }
      } else {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      }
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
          reset();
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
        <ErrorBanner
          className="mb-3"
          message={t(`chat.errors.${error}`, { defaultValue: error })}
        />
      )}
      <div className="flex h-full min-h-0 flex-col lg:flex-row">
        <div className="mb-2 flex shrink-0 items-center gap-2 lg:hidden">
          <button
            type="button"
            onClick={handleNewChat}
            disabled={newChatDisabled}
            aria-busy={creatingChat}
            aria-label={newChatLabel}
            title={creatingChat ? undefined : newChatShortcut}
            className="rounded-lg border border-nn-border px-3 py-1.5 text-sm text-gray-900 transition-colors hover:bg-nn-gray-light disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            {newChatLabel}
          </button>
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
          onSelect={handleSelectSession}
          onDelete={handleDeleteSession}
          onNewChat={handleNewChat}
          newChatLoading={creatingChat}
          newChatDisabled={newChatDisabled}
          sessionId={activeId}
          sessionTitle={activeSession?.title}
          messages={messages}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col lg:pl-4">
          <ChatWindow
            messages={messages}
            retrievalTrace={retrievalTrace}
            answerPhase={phase}
            answerFailReason={failReason}
            answerMode={mode}
            streamingDraft={streamingDraft}
            streamingComplete={streamingComplete}
            streamingUxEnabled={streamingUxEnabled}
          />
          <ChatInput ref={chatInputRef} onSend={handleSend} disabled={isActive} />
        </div>
      </div>
    </PageShell>
  );
}
