<template>
  <div class="page">
    <div class="app-shell">
      <header class="header">
        <div class="header-left">
          <div class="logo-wrap">
            <div class="logo-dot" />
            <span class="logo-text">Cover Insight</span>
          </div>
          <div class="account-inline">
            <p v-if="token" class="account-status">
              已登录：
              <span class="tag tag-solid">{{ phone }}</span>
            </p>
            <p v-else class="account-status">
              游客模式 · 剩余
              <span class="strong-number">{{ remainingGuestQuota }}</span>
              / 3 次
            </p>
            <button class="btn btn-outline btn-sm" @click="handleLoginClick">
              {{ token ? "切换账号" : "登录 / 注册" }}
            </button>
          </div>
        </div>
        <div class="header-text">
          <h1>植被盖度识别</h1>
          <p class="subtitle">上传一张照片，快速获得植被覆盖比例</p>
        </div>
      </header>

      <main class="content">

        <section class="card card-upload">
          <div class="card-header">
            <h2>上传或拍摄照片</h2>
            <p class="card-desc">建议选择画面清晰、无遮挡的地块照片，单次仅支持一张。</p>
          </div>
          <div class="card-body upload-body">
            <div class="upload-actions">
              <label class="upload-label">
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  @change="onFileChange"
                  class="file-input"
                />
                <span class="upload-label-text">选择或拍摄照片</span>
              </label>
              <button class="btn btn-primary" :disabled="!selectedFile || loading" @click="upload">
                {{ loading ? "正在识别..." : "开始识别" }}
              </button>
            </div>
            <p class="hint">系统暂不支持批量识别，请一次上传一张照片。</p>
          </div>
        </section>

        <section v-if="previewUrl" class="card card-result">
          <div class="card-header">
            <h2>原始图片预览</h2>
          </div>
          <div class="card-body">
            <div class="image-frame">
              <img :src="previewUrl" alt="预览图" class="preview-img" />
            </div>
          </div>
        </section>

        <section v-if="resultCoverage !== null" class="card card-result">
          <div class="card-header result-header">
            <h2>识别结果</h2>
            <div class="metric">
              <span class="metric-label">植被盖度</span>
              <span class="metric-value">{{ (resultCoverage * 100).toFixed(2) }}%</span>
            </div>
          </div>
          <div class="card-body">
            <p class="metric-sub">
              结果仅供快速评估使用，实际调研请结合现场情况和历史数据综合判断。
            </p>
            <div v-if="token && lastAnalysisId" class="result-actions">
              <button class="btn btn-outline btn-sm" :disabled="saving" @click="saveCurrent">
                {{ saving ? "保存中..." : "保存本次记录" }}
              </button>
            </div>
            <div v-if="maskImageUrl" class="mask-wrapper">
              <h3>掩膜图</h3>
              <div class="image-frame">
                <img :src="maskImageUrl" alt="掩膜图" class="preview-img" />
              </div>
            </div>
          </div>
        </section>

        <section v-if="token" class="card card-history">
          <div class="card-header history-header">
            <h2>已保存记录</h2>
            <button class="btn btn-ghost btn-sm" :disabled="loadingSaved" @click="fetchSavedRecords">
              {{ loadingSaved ? "刷新中..." : "刷新" }}
            </button>
          </div>
          <div class="card-body history-body">
            <p v-if="!savedRecords.length" class="hint">
              暂时还没有保存的记录，完成一次识别后可以选择“保存本次记录”。
            </p>
            <ul v-else class="history-list">
              <li v-for="item in savedRecords" :key="item.id" class="history-item">
                <div class="history-main">
                  <div class="history-top">
                    <span class="history-coverage">{{ (item.coverage * 100).toFixed(1) }}%</span>
                    <span class="history-time">{{ formatTime(item.created_at) }}</span>
                  </div>
                  <img
                    v-if="item.thumb_url"
                    :src="item.thumb_url"
                    alt="缩略图"
                    class="history-thumb"
                  />
                </div>
                <button class="btn btn-outline btn-sm" @click="previewSaved(item)">查看</button>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="errorMessage" class="alert alert-error">
          {{ errorMessage }}
        </section>
      </main>

      <footer class="footer">
        <span>© {{ new Date().getFullYear() }} 植被盖度识别 · 实验工具</span>
      </footer>
    </div>
    <div v-if="showLoginPanel" class="modal-backdrop">
      <div class="modal-card">
        <div class="modal-header">
          <h2>手机号登录 / 注册</h2>
        </div>
        <div class="modal-body">
          <div class="login-field">
            <label for="login-phone">手机号</label>
            <input
              id="login-phone"
              v-model="loginPhone"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              placeholder="请输入手机号"
              class="login-input"
            />
          </div>
          <div class="login-actions">
            <button class="btn btn-primary btn-sm" :disabled="loginLoading" @click="submitLogin">
              {{ loginLoading ? "登录中..." : "确认登录" }}
            </button>
            <button class="btn btn-ghost btn-sm" :disabled="loginLoading" @click="closeLoginPanel">
              取消
            </button>
          </div>
          <p class="login-tip">当前版本不进行验证码校验，仅用于区分账号与解除次数限制。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

// 后端基础地址（开发环境下会被 Vite 代理）
const API_BASE = "";

const token = ref<string | null>(localStorage.getItem("cover_token"));
const phone = ref<string | null>(localStorage.getItem("cover_phone"));
const guestId = ref<string | null>(localStorage.getItem("cover_guest_id"));
const guestUsed = ref<number | null>(
  localStorage.getItem("cover_guest_used")
    ? Number(localStorage.getItem("cover_guest_used"))
    : null
);

const selectedFile = ref<File | null>(null);
const previewUrl = ref<string | null>(null);
const resultCoverage = ref<number | null>(null);
const maskImageUrl = ref<string | null>(null);
const loading = ref(false);
const loginLoading = ref(false);
const errorMessage = ref<string | null>(null);
const lastAnalysisId = ref<number | null>(null);
const saving = ref(false);

type SavedRecord = {
  id: number;
  coverage: number;
  created_at: string;
  mask_url: string;
  thumb_url: string;
};

const savedRecords = ref<SavedRecord[]>([]);
const loadingSaved = ref(false);

const fileInput = ref<HTMLInputElement | null>(null);

const guestUsedDisplay = computed(() =>
  guestUsed.value === null || Number.isNaN(guestUsed.value) ? 0 : guestUsed.value
);

const remainingGuestQuota = computed(() => {
  const used = guestUsed.value ?? 0;
  const limit = 3;
  const rest = limit - used;
  return rest > 0 ? rest : 0;
});

const showLoginPanel = ref(false);
const loginPhone = ref("");

function handleLoginClick() {
  showLoginPanel.value = true;
  loginPhone.value = phone.value || "";
  errorMessage.value = null;
}

function closeLoginPanel() {
  showLoginPanel.value = false;
}

function submitLogin() {
  const value = loginPhone.value.trim();
  if (!value) {
    errorMessage.value = "请输入手机号。";
    return;
  }

  loginLoading.value = true;
  errorMessage.value = null;

  fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ phone: value })
  })
    .then(async (res) => {
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data && data.detail) || "登录失败");
      }
      return res.json();
    })
    .then((data: { token: string; phone: string; is_new: boolean }) => {
      token.value = data.token;
      phone.value = data.phone;
      localStorage.setItem("cover_token", data.token);
      localStorage.setItem("cover_phone", data.phone);
      // 登录后游客限制不再生效，可清空游客计数
      guestId.value = null;
      guestUsed.value = null;
      localStorage.removeItem("cover_guest_id");
      localStorage.removeItem("cover_guest_used");
      if (data.is_new) {
        window.alert("注册成功，已为您自动登录。");
      } else {
        window.alert("登录成功。");
      }
      showLoginPanel.value = false;
      fetchSavedRecords();
    })
    .catch((err: Error) => {
      errorMessage.value = err.message;
    })
    .finally(() => {
      loginLoading.value = false;
    });
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = input.files;
  if (!files || files.length === 0) return;

  const file = files[0];
  selectedFile.value = file;
  resultCoverage.value = null;
  maskImageUrl.value = null;
  errorMessage.value = null;

  if (previewUrl.value && previewUrl.value.startsWith("blob:")) {
    URL.revokeObjectURL(previewUrl.value);
  }
  previewUrl.value = URL.createObjectURL(file);
}

function upload() {
  if (!selectedFile.value) {
    window.alert("请先选择一张图片。");
    return;
  }

  loading.value = true;
  errorMessage.value = null;

  const formData = new FormData();
  formData.append("file", selectedFile.value);
  if (!token.value && guestId.value) {
    formData.append("guest_id", guestId.value);
  }

  const headers: Record<string, string> = {};
  if (token.value) {
    headers["Authorization"] = `Bearer ${token.value}`;
  }

  fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
    headers
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (data && data.detail) || "识别失败";
        throw new Error(msg);
      }
      return data as {
        id: number;
        coverage: number;
        mask_url: string;
        guest_id?: string | null;
        guest_used?: number | null;
        guest_limit?: number | null;
      };
    })
    .then((data) => {
      lastAnalysisId.value = data.id;
      resultCoverage.value = data.coverage;
      // 掩膜图为后端静态资源，相对路径即可由 Vite 代理到 8000 端口
      maskImageUrl.value = data.mask_url;

      if (!token.value && data.guest_id) {
        guestId.value = data.guest_id;
        localStorage.setItem("cover_guest_id", data.guest_id);
      }
      if (!token.value && typeof data.guest_used === "number") {
        guestUsed.value = data.guest_used;
        localStorage.setItem("cover_guest_used", String(data.guest_used));
      }
    })
    .catch((err: Error) => {
      errorMessage.value = err.message;
    })
    .finally(() => {
      loading.value = false;
    });
}

function fetchSavedRecords() {
  if (!token.value) return;

  loadingSaved.value = true;
  errorMessage.value = null;

  fetch(`${API_BASE}/api/analyses/saved?limit=20`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token.value}`
    }
  })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = (data && data.detail) || "获取保存记录失败";
        throw new Error(msg);
      }
      return data as SavedRecord[];
    })
    .then((data) => {
      savedRecords.value = data;
    })
    .catch((err: Error) => {
      errorMessage.value = err.message;
    })
    .finally(() => {
      loadingSaved.value = false;
    });
}

function saveCurrent() {
  if (!token.value) {
    window.alert("请先登录后再保存记录。");
    handleLoginClick();
    return;
  }
  if (!lastAnalysisId.value) {
    window.alert("当前没有可保存的识别结果。");
    return;
  }

  saving.value = true;
  errorMessage.value = null;

  fetch(`${API_BASE}/api/analyses/${lastAnalysisId.value}/save`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token.value}`
    }
  })
    .then(async (res) => {
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const msg = (data && data.detail) || "保存记录失败";
        throw new Error(msg);
      }
      return res.json().catch(() => ({}));
    })
    .then(() => {
      fetchSavedRecords();
      window.alert("已保存到记录列表。");
    })
    .catch((err: Error) => {
      errorMessage.value = err.message;
    })
    .finally(() => {
      saving.value = false;
    });
}

function previewSaved(item: SavedRecord) {
  resultCoverage.value = item.coverage;
  maskImageUrl.value = item.mask_url;
  previewUrl.value = item.thumb_url;
}

function formatTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const y = d.getFullYear();
  const m = `${d.getMonth() + 1}`.padStart(2, "0");
  const day = `${d.getDate()}`.padStart(2, "0");
  const h = `${d.getHours()}`.padStart(2, "0");
  const mm = `${d.getMinutes()}`.padStart(2, "0");
  return `${y}-${m}-${day} ${h}:${mm}`;
}

onMounted(() => {
  if (token.value) {
    fetchSavedRecords();
  }
});

onBeforeUnmount(() => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
});
</script>

<style scoped>
/* 页面整体布局：全屏渐变背景 + 居中卡片布局 */
.page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  padding: 20px;
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1e293b;
}

.app-shell {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 24px;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.05),
    0 8px 10px -6px rgba(0, 0, 0, 0.01),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  display: flex;
  flex-direction: column;
  padding: 24px;
  box-sizing: border-box;
  gap: 24px;
}

/* Header */
.header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.header-left {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-dot {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.2);
  position: relative;
}

.logo-dot::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  background-color: rgba(255,255,255,0.2);
  border-radius: 50%;
}

.logo-text {
  font-weight: 800;
  font-size: 18px;
  letter-spacing: -0.02em;
  color: #15803d;
}

.header-text h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}

.subtitle {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.5;
}

.account-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-status {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Content */
.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Cards */
.card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.02),
    0 2px 4px -2px rgba(0, 0, 0, 0.02),
    0 0 0 1px rgba(226, 232, 240, 0.6);
  padding: 20px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 10px 15px -3px rgba(0, 0, 0, 0.05),
    0 4px 6px -4px rgba(0, 0, 0, 0.02),
    0 0 0 1px rgba(226, 232, 240, 0.8);
}

.card-header {
  margin-bottom: 16px;
}

.card-header h2 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header h2::before {
  content: '';
  display: block;
  width: 4px;
  height: 16px;
  background: #22c55e;
  border-radius: 2px;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
}

/* Upload Area */
.upload-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.upload-label {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border-radius: 12px;
  background-color: #f8fafc;
  border: 2px dashed #cbd5e1;
  color: #475569;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-label:hover {
  border-color: #22c55e;
  background-color: #f0fdf4;
  color: #16a34a;
}

.file-input {
  display: none;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  line-height: 1;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
  border-radius: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #16a34a, #15803d);
  transform: translateY(-1px);
  box-shadow: 0 6px 8px -1px rgba(22, 163, 74, 0.4);
}

.btn-primary:disabled {
  background: #cbd5e1;
  color: #f1f5f9;
  box-shadow: none;
  cursor: not-allowed;
}

.btn-outline {
  background: white;
  border: 1px solid #e2e8f0;
  color: #475569;
}

.btn-outline:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
  color: #1e293b;
}

.btn-ghost {
  background: transparent;
  color: #64748b;
}

.btn-ghost:hover {
  background: #f1f5f9;
  color: #334155;
}

/* Result Area */
.image-frame {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: center;
  align-items: center;
}

.preview-img {
  width: 100%;
  height: auto;
  display: block;
}

.result-header {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.metric-label {
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 32px;
  font-weight: 800;
  color: #16a34a;
  line-height: 1;
  letter-spacing: -0.02em;
}

.metric-sub {
  background: #f0fdf4;
  color: #166534;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 16px;
  border: 1px solid #bbf7d0;
}

.mask-wrapper {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f1f5f9;
}

.mask-wrapper h3 {
  font-size: 14px;
  color: #475569;
  margin-bottom: 12px;
}

/* History */
.history-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.history-item:hover {
  background: white;
  border-color: #e2e8f0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.history-main {
  display: flex;
  flex-direction: row-reverse;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.history-thumb {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  object-fit: cover;
  background: #e2e8f0;
  border: 1px solid rgba(0,0,0,0.05);
}

.history-top {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.history-coverage {
  font-weight: 700;
  color: #16a34a;
  font-size: 16px;
  line-height: 1.2;
}

.history-time {
  font-size: 12px;
  color: #94a3b8;
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}

.modal-card {
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.login-input {
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 16px;
  box-sizing: border-box;
  margin-top: 4px;
}

.login-input:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
}

/* Tags */
.tag {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.tag-solid {
  background: #dcfce7;
  color: #15803d;
}

.strong-number {
  font-weight: 700;
  color: #16a34a;
}

/* Footer */
.footer {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  padding-top: 20px;
}

/* Alert */
.alert {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.alert-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

/* Responsive */
@media (max-width: 640px) {
  .page {
    padding: 0;
    background: #f8fafc;
  }
  
  .app-shell {
    border-radius: 0;
    min-height: 100vh;
    box-shadow: none;
    padding: 16px;
  }

  .header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .account-inline {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
