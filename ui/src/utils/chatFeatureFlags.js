export function isStreamingUxEnabled() {
  return import.meta.env.VITE_CHAT_STREAMING_UX === 'true';
}
