import { createApp } from "vue";
import App from "./App.vue";

// 注册 Service Worker，启用 PWA 能力
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) => console.error("ServiceWorker 注册失败", err));
  });
}

createApp(App).mount("#app");

