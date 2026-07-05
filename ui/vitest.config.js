import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
    fileParallelism: false,
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
  },
});
