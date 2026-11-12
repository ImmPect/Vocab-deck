/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// Сборщик и dev-сервер (раздел 4.1.2 ПР3).
// В разработке запросы /api проксируются на FastAPI: страница и API на одном origin,
// поэтому cookie session_id (SameSite=Lax, Path=/api) работает без настройки CORS.
export default defineConfig(({ mode }) => {
  // Каталог проекта, а не текущий: dev-сервер может запускаться из корня репозитория
  const env = loadEnv(mode, fileURLToPath(new URL('.', import.meta.url)), '');
  return {
    base: env.VITE_BASE ?? '/',
    plugins: [react()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': { target: env.VITE_API_PROXY ?? 'http://127.0.0.1:8000', changeOrigin: false },
      },
    },
    build: {
      target: 'es2020',
      // Отчёт о сжатом размере чанков — проверка бюджета NFR-P-04 (scripts/postbuild.mjs)
      reportCompressedSize: true,
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
  };
});
