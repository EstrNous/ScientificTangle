import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const E2E_ENV = {
  VITE_USE_MOCK: 'false',
  VITE_REVIEW_CONSOLE_ENABLED: 'true',
  VITE_LIVE_NOTIFICATIONS_ENABLED: 'true',
  VITE_CHAT_LIFECYCLE_SIMULATION: 'false',
  VITE_CHAT_STREAMING_UX: 'false',
};

function e2eDefine(mode) {
  if (mode !== 'e2e') {
    return {};
  }
  return Object.fromEntries(
    Object.entries(E2E_ENV).map(([key, value]) => [`import.meta.env.${key}`, JSON.stringify(value)]),
  );
}

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: e2eDefine(mode),
  esbuild: {
    jsx: 'automatic',
  },
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api/auth': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    port: 3000,
  },
}));
