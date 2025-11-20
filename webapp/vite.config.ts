import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 使用 Vite + Vue3 构建前端，并作为 PWA 外壳
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 开发时将 API 请求代理到后端 FastAPI 服务
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true
      },
      "/static": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: "dist"
  }
});

