import { useEffect, useState } from 'react';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { ChatSidebar, ChatWindow, ChatInput } from '../components/chat/index.js';
import { apiGet } from '../api/client.js';

export default function ChatPage() {
  const [loading, setLoading] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [subgraph, setSubgraph] = useState(null);

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
    apiGet(`/chat/sessions/${activeId}/messages`).then(setMessages);
  }, [activeId]);

  if (loading) return <Loader />;

  const handleSend = ({ text, files }) => {
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
          <ChatWindow messages={messages} />
          <ChatInput onSend={handleSend} />
        </div>
      </div>
    </PageShell>
  );
}
