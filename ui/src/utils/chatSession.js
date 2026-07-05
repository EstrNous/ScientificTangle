export function sessionTitleFromText(text, fallbackTitle) {
  const trimmed = text.trim();
  if (!trimmed) return fallbackTitle;
  return trimmed.length > 64 ? `${trimmed.slice(0, 61)}…` : trimmed;
}

export function isEmptyDraftSession(session, messages, defaultTitle) {
  if (!session || messages.length > 0) return false;
  return session.title === defaultTitle;
}

export function findReusableEmptyDraftSession(
  sessions,
  activeId,
  activeMessages,
  defaultTitle,
  messagesBySessionId = {},
) {
  const activeSession = sessions.find((session) => session.id === activeId);
  if (isEmptyDraftSession(activeSession, activeMessages, defaultTitle)) {
    return activeSession;
  }
  return (
    sessions.find((session) => {
      if (session.id === activeId || session.title !== defaultTitle) return false;
      const sessionMessages = session.id === activeId ? activeMessages : messagesBySessionId[session.id];
      return !sessionMessages || sessionMessages.length === 0;
    }) ?? null
  );
}
