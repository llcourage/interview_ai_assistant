import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 使用绝对路径，确保在Web部署（Vercel）时静态资源路径正确
  // 当访问 /auth/callback 等路由时，相对路径会导致资源加载失败
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true
  },
  server: {
    port: 5173,
    strictPort: true // 如果 5173 被占用就直接报错，而不是自动跳到其他端口
  }
})

