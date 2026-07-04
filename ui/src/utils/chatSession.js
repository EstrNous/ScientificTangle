export function sessionTitleFromText(text, fallbackTitle) {
  const trimmed = text.trim();
  if (!trimmed) return fallbackTitle;
  return trimmed.length > 64 ? `${trimmed.slice(0, 61)}…` : trimmed;
}

export function isEmptyDraftSession(session, messages, defaultTitle) {
  if (!session || messages.length > 0) return false;
  return session.title === defaultTitle;
}
