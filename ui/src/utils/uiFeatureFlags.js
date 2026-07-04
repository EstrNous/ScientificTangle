import { useMock } from '../api/client.js';

function readFlag(name, defaultValue = false) {
  const raw = import.meta.env[name];
  if (raw == null || raw === '') {
    return defaultValue;
  }
  return raw === 'true' || raw === '1';
}

export function isDevRoleSwitcherEnabled() {
  return useMock || import.meta.env.DEV;
}

export function isProductionAuthMode() {
  return !useMock && !import.meta.env.DEV;
}

export function isLiveProductionMode() {
  return !useMock;
}

export function isServerExportEnabled() {
  if (!useMock) {
    return true;
  }
  return readFlag('VITE_SERVER_EXPORT_ENABLED', false);
}

export function isClientExportFallbackEnabled() {
  return readFlag('VITE_CLIENT_EXPORT_FALLBACK_ENABLED', false);
}

export function isLiveNotificationsEnabled() {
  return readFlag('VITE_LIVE_NOTIFICATIONS_ENABLED', false);
}

export function isReviewConsoleEnabled() {
  return readFlag('VITE_REVIEW_CONSOLE_ENABLED', false);
}

export function isReviewActionsEnabled() {
  if (useMock) {
    return true;
  }
  return isReviewConsoleEnabled();
}

export function isSourceLiveModeEnabled() {
  if (readFlag('VITE_SOURCE_LIVE_MODE', false)) {
    return true;
  }
  return !useMock;
}
