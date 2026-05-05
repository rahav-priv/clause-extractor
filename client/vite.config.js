import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const serverPort = process.env.CLAUSE_EXTRACTOR_PORT || 6363

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: `http://localhost:${serverPort}`,
        changeOrigin: true,
      },
    },
  },
})
