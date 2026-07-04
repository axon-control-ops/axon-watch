import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  worker: {
    format: 'es',
  },
  server: {
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_CONTROL_PLANE_BASE_URL ?? 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    },
  },
});
