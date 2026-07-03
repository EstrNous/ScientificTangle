import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ChatSidebar, ChatWindow, ChatInput } from '../components/chat/index.js';
import { apiGet } from '../api/client.js';
import { runMockChatQuery } from '../api/mock/chatQuery.js';

export default function ChatPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [subgraph, setSubgraph] = useState(null);
  const [retrievalTrace, setRetrievalTrace] = useState(null);
  const [isQuerying, setIsQuerying] = useState(false);

  useEffect(() => {
    Promise.all([apiGet('/chat/sessions'), apiGet('/graph/subgraph')])
      .then(([s, g]) => {
        setSessions(s);
        setActiveId(s[0]?.id ?? null);
        setSubgraph(g.subgraph);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!activeId) return;
    setRetrievalTrace(null);
    apiGet(`/chat/sessions/${activeId}/messages`).then(setMessages);
  }, [activeId]);

  if (loading) return <Loader />;

  const handleSend = async ({ text, files }) => {
    if (isQuerying) return;

    const attachments = files.map((f) => f.name);
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        role: 'user',
        content: text,
        attachments,
      },
    ]);

    setIsQuerying(true);
    setRetrievalTrace({ steps: [], activeStepId: null });

    try {
      const reply = await runMockChatQuery(
        { text, files },
        {
          t,
          onStep: setRetrievalTrace,
          stepDelayMs: 650,
        },
      );
      setRetrievalTrace(null);
      setMessages((prev) => [...prev, reply]);
    } finally {
      setIsQuerying(false);
      setRetrievalTrace(null);
    }
  };

  const handleDeleteSession = (id) => {
    setSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (activeId === id) {
        const nextActive = next[0]?.id ?? null;
        setActiveId(nextActive);
        if (!nextActive) setMessages([]);
      }
      return next;
    });
  };

  const activeSession = sessions.find((s) => s.id === activeId);

  return (
    <PageShell>
      <div className="flex h-full min-h-0">
        <ChatSidebar
          sessions={sessions}
          activeId={activeId}
          onSelect={setActiveId}
          onDelete={handleDeleteSession}
          sessionId={activeId}
          sessionTitle={activeSession?.title}
          messages={messages}
          subgraph={subgraph}
        />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col pl-4">
          <ChatWindow messages={messages} retrievalTrace={retrievalTrace} />
          <ChatInput onSend={handleSend} disabled={isQuerying} />
        </div>
      </div>
    </PageShell>
  );
}
