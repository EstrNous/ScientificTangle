import axios from 'axios';
import { useMock } from '../utils/runtimeMode.js';
import { ROLES, useAuthStore } from '../stores/authStore.js';

const authHttp = axios.create({
  baseURL: import.meta.env.VITE_AUTH_URL || '',
  timeout: 30000,
  withCredentials: true,
});

const ROLE_MAP = {
  admin: ROLES.ADMIN,
  researcher: ROLES.RESEARCHER,
  analyst: ROLES.ANALYST,
  manager: ROLES.DIRECTOR,
  external_partner: ROLES.EXTERNAL_PARTNER,
};

const MOCK_ROLE_BY_USERNAME = {
  admin: ROLES.ADMIN,
  researcher: ROLES.RESEARCHER,
  analyst: ROLES.ANALYST,
  manager: ROLES.DIRECTOR,
  director: ROLES.DIRECTOR,
  external_partner: ROLES.EXTERNAL_PARTNER,
};

function resolveMockAuth(identifier) {
  const normalized = identifier.trim().toLowerCase();
  const username = normalized.includes('@') ? normalized.split('@')[0] : normalized;
  const role = MOCK_ROLE_BY_USERNAME[username] ?? ROLES.RESEARCHER;
  const backendRole =
    role === ROLES.DIRECTOR
      ? 'manager'
      : role === ROLES.EXTERNAL_PARTNER
        ? 'external_partner'
        : role;

  return {
    accessToken: 'mock-access-token',
    user: {
      id: '00000000-0000-0000-0000-000000000001',
      username,
      email: normalized.includes('@') ? normalized : `${username}@example.com`,
      role: backendRole,
      is_active: true,
    },
    role,
  };
}

function applyMockAuth(identifier) {
  const auth = resolveMockAuth(identifier);
  useAuthStore.getState().setAuth(auth);
  return auth.accessToken;
}

export function applyAuthResponse(data) {
  const role = ROLE_MAP[data.user?.role] ?? useAuthStore.getState().role;
  useAuthStore.getState().setAuth({
    accessToken: data.access_token,
    user: data.user,
    role,
  });
  return data;
}

export function mapAuthError(error) {
  return error?.response?.data?.code ?? 'unknown';
}

export async function login(identifier, password) {
  const { data } = await authHttp.post('/api/auth/login', { identifier, password });
  return applyAuthResponse(data);
}

export async function register(username, email, password) {
  const { data } = await authHttp.post('/api/auth/register', { username, email, password });
  return applyAuthResponse(data);
}

export async function refreshSession() {
  const { data } = await authHttp.post('/api/auth/refresh');
  applyAuthResponse(data);
  return data.access_token;
}

export async function restoreLiveSession() {
  const state = useAuthStore.getState();
  if (state.accessToken) {
    try {
      await fetchCurrentUser();
      return state.accessToken;
    } catch {
      useAuthStore.getState().clearAuth();
    }
  }
  const accessToken = await refreshSession();
  await fetchCurrentUser();
  return accessToken;
}

export async function ensureAuth() {
  const state = useAuthStore.getState();
  if (state.accessToken) return state.accessToken;

  if (!useMock) {
    return restoreLiveSession();
  }

  const identifier = import.meta.env.VITE_AUTH_USERNAME;
  const password = import.meta.env.VITE_AUTH_PASSWORD;
  if (!identifier || !password) {
    throw new Error('auth_credentials_missing');
  }

  return applyMockAuth(identifier);
}

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}

function authorizedConfig() {
  const token = useAuthStore.getState().accessToken;
  return token ? { headers: authHeaders(token) } : {};
}

export async function fetchCurrentUser() {
  if (useMock) {
    const state = useAuthStore.getState();
    if (state.user) return state.user;
    const identifier = import.meta.env.VITE_AUTH_USERNAME ?? 'researcher';
    await ensureAuth();
    return useAuthStore.getState().user;
  }

  const { data } = await authHttp.get('/api/auth/me', authorizedConfig());
  const role = ROLE_MAP[data.role] ?? useAuthStore.getState().role;
  useAuthStore.getState().setAuth({
    accessToken: useAuthStore.getState().accessToken,
    user: data,
    role,
  });
  return data;
}

export async function updateProfile({ currentPassword, username, email }) {
  if (useMock) {
    const state = useAuthStore.getState();
    const user = {
      ...state.user,
      username: username ?? state.user?.username,
      email: email ?? state.user?.email,
    };
    useAuthStore.getState().setAuth({
      accessToken: state.accessToken,
      user,
      role: state.role,
    });
    return user;
  }

  const payload = { current_password: currentPassword };
  if (username) payload.username = username;
  if (email) payload.email = email;
  const { data } = await authHttp.patch('/api/auth/me', payload, authorizedConfig());
  const role = ROLE_MAP[data.role] ?? useAuthStore.getState().role;
  useAuthStore.getState().setAuth({
    accessToken: useAuthStore.getState().accessToken,
    user: data,
    role,
  });
  return data;
}

export async function changePassword({ currentPassword, newPassword }) {
  if (useMock) {
    return {
      access_token: useAuthStore.getState().accessToken,
      user: useAuthStore.getState().user,
    };
  }

  const { data } = await authHttp.post(
    '/api/auth/change-password',
    { current_password: currentPassword, new_password: newPassword },
    authorizedConfig(),
  );
  return applyAuthResponse(data);
}

export async function logout() {
  let error;
  try {
    if (!useMock) {
      await authHttp.post('/api/auth/logout', {}, authorizedConfig());
    }
  } catch (caught) {
    error = caught;
  } finally {
    useAuthStore.getState().clearAuth();
  }
  if (error) {
    throw error;
  }
}

export async function logoutAll() {
  let error;
  try {
    if (!useMock) {
      await authHttp.post('/api/auth/logout-all', {}, authorizedConfig());
    }
  } catch (caught) {
    error = caught;
  } finally {
    useAuthStore.getState().clearAuth();
  }
  if (error) {
    throw error;
  }
}

export async function deactivateAccount(currentPassword) {
  if (!useMock) {
    await authHttp.delete('/api/auth/me', {
      ...authorizedConfig(),
      data: { current_password: currentPassword },
    });
  }
  useAuthStore.getState().clearAuth();
}
