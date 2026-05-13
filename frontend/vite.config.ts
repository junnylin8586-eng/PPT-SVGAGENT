import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5200,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://localhost:5031',
        changeOrigin: true,
        timeout: 300000,  // 5 min timeout for LLM calls (SSE streams)
        proxyTimeout: 300000,
      },
    },
  },
})
