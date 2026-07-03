import axios from 'axios';
import { useAuthStore } from '../stores/authStore.js';

const authHttp = axios.create({
  baseURL: import.meta.env.VITE_AUTH_URL || '',
  timeout: 30000,
  withCredentials: true,
});

const ROLE_MAP = {
  admin: 'admin',
  researcher: 'researcher',
  analyst: 'analyst',
  manager: 'director',
  external_partner: 'external_partner',
};

export async function login(identifier, password) {
  const { data } = await authHttp.post('/api/auth/login', { identifier, password });
  return data;
}

export async function ensureAuth() {
  const state = useAuthStore.getState();
  if (state.accessToken) return state.accessToken;

  const identifier = import.meta.env.VITE_AUTH_USERNAME;
  const password = import.meta.env.VITE_AUTH_PASSWORD;
  if (!identifier || !password) {
    throw new Error('auth_credentials_missing');
  }

  const data = await login(identifier, password);
  const role = ROLE_MAP[data.user?.role] ?? state.role;
  useAuthStore.getState().setAuth({
    accessToken: data.access_token,
    user: data.user,
    role,
  });
  return data.access_token;
}

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` };
}
