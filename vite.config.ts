import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 使用相对路径，兼容 Electron 和 Web 部署
  // Electron 需要相对路径，Vercel 也能正确处理相对路径
  base: './',
  build: {
    outDir: 'dist',
    emptyOutDir: true
  },
  server: {
    port: 5173
  }
})

