const STORAGE_KEY = 'st_user_interests';

function readAll() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeAll(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function loadUserInterests(userId) {
  if (!userId) return { rawText: '', interests: [] };
  const entry = readAll()[userId];
  return entry ?? { rawText: '', interests: [] };
}

export function saveUserInterests(userId, rawText, interests) {
  if (!userId) return;
  const data = readAll();
  data[userId] = {
    rawText,
    interests,
    updatedAt: new Date().toISOString(),
  };
  writeAll(data);
}
