import { apiDelete, apiGet, apiPost } from './client.js';
import { normalizeListResponse } from '../utils/listResponse.js';

const real = { real: true };

export function fetchChatSessions() {
  return apiGet('/chat/sessions', real).then(normalizeListResponse);
}

export function createChatSession(title) {
  return apiPost('/chat/sessions', { title }, real);
}

export function deleteChatSession(sessionId) {
  return apiDelete(`/chat/sessions/${sessionId}`, real);
}

export function fetchChatMessages(sessionId) {
  return apiGet(`/chat/sessions/${sessionId}/messages`, real).then(normalizeListResponse);
}

export function sendChatMessage(sessionId, content) {
  return apiPost(`/chat/sessions/${sessionId}/messages`, { content }, real);
}
