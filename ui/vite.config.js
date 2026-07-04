import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const DEMO_ENV = {
  VITE_USE_MOCK: 'false',
  VITE_REVIEW_CONSOLE_ENABLED: 'true',
  VITE_LIVE_NOTIFICATIONS_ENABLED: 'true',
  VITE_CHAT_LIFECYCLE_SIMULATION: 'false',
  VITE_CHAT_STREAMING_UX: 'false',
};

function modeDefine(mode) {
  if (mode === 'e2e') {
    return Object.fromEntries(
      Object.entries(DEMO_ENV).map(([key, value]) => [`import.meta.env.${key}`, JSON.stringify(value)]),
    );
  }
  if (mode === 'mock') {
    return {
      'import.meta.env.VITE_USE_MOCK': JSON.stringify('true'),
    };
  }
  return {
    'import.meta.env.VITE_USE_MOCK': JSON.stringify(process.env.VITE_USE_MOCK ?? 'false'),
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  define: modeDefine(mode),
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
