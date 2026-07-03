import axios from 'axios';
import { mockFetch } from './mock/index.js';

const useMock = import.meta.env.VITE_USE_MOCK !== 'false';
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const http = axios.create({ baseURL, timeout: 120000 });

export async function apiGet(path, options = {}) {
  if (useMock) {
    return mockFetch(path.replace(/^\//, ''), options);
  }
  const { data } = await http.get(path);
  return data;
}

export async function apiPost(path, body, options = {}) {
  if (useMock) {
    return mockFetch(path.replace(/^\//, ''), { ...options, method: 'POST', body });
  }
  const { data } = await http.post(path, body);
  return data;
}

export { useMock };
