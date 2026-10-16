import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // 127.0.0.1 (not localhost) so the proxy never resolves to IPv6 ::1
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
