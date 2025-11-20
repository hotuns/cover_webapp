import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

// Vitest 配置，仅做最小单元测试示例
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom"
  }
});

