import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

const controlPlaneProxy = {
  '/api': {
    target: process.env.VITE_CONTROL_PLANE_BASE_URL ?? 'http://127.0.0.1:8787',
    changeOrigin: true,
    ws: true,
  },
};

export default defineConfig({
  plugins: [vue()],
  worker: {
    format: 'es',
  },
  server: {
    strictPort: true,
    proxy: controlPlaneProxy,
  },
  preview: {
    proxy: controlPlaneProxy,
  },
});
