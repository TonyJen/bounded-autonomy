import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/status': 'http://localhost:8010',
      '/history': 'http://localhost:8010',
      '/health': 'http://localhost:8010',
      '/evals': 'http://localhost:8010',
      '/sim': 'http://localhost:8010',
      '/ws': { target: 'ws://localhost:8010', ws: true },
    },
  },
  test: { environment: 'jsdom', globals: true },
})
