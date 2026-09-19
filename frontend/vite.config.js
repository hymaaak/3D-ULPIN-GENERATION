import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // Inside docker-compose the backend hostname is `backend`; on a
        // bare-metal dev machine it is localhost.
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: (process.env.VITE_PROXY_TARGET || 'http://localhost:8000').replace(/^http/, 'ws'),
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
