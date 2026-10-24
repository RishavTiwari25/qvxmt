/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In dev the FastAPI app runs on :8000; in prod nginx / Vercel route /api instead.
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
