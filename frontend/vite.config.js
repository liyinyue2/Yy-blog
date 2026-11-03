import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    // 本机 Windows 把 TCP 5141–5240 列为排除端口段，5173 绑定必然 EACCES，改用 8080
    port: 8080,
    proxy: {
      '/api': { target: 'http://127.0.0.1:3002', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
