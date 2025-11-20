#!/usr/bin/env bash

# 简单快速部署脚本（开发 / 测试用）
# 说明：
# - 假设服务器已经安装好：uv、Python 3.12+、Node.js、npm
# - 不考虑安全与性能，仅用于一键拉起后端 API 和前端页面
# - 在项目根目录下执行：bash deploy_quick.sh

set -e

# 项目根目录
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> 项目根目录: ${ROOT_DIR}"

#######################################
# 1. 启动后端（FastAPI + uv）
#######################################
echo ">>> [后端] 安装依赖并启动服务..."

cd "${ROOT_DIR}/cover_webapp_backend"

# 使用本地缓存目录，避免写入全局缓存
export UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"

echo ">>> [后端] 使用 UV_CACHE_DIR=${UV_CACHE_DIR}"

# 同步 Python 依赖
uv sync

# 后端端口：8000（在 __init__.py 中配置）
BACKEND_PORT=8000

echo ">>> [后端] 通过 uv 启动 FastAPI（端口 ${BACKEND_PORT}）..."
nohup uv run cover-webapp-backend > "${ROOT_DIR}/backend.log" 2>&1 &
BACKEND_PID=$!
echo ">>> [后端] 已启动，PID=${BACKEND_PID}，日志：${ROOT_DIR}/backend.log"

#######################################
# 2. 启动前端（Vite 构建 + preview）
#######################################
echo ">>> [前端] 安装依赖、构建并启动预览服务..."

cd "${ROOT_DIR}/webapp"

if [ ! -d node_modules ]; then
  echo ">>> [前端] 检测到首次运行，执行 npm install..."
  npm install
fi

echo ">>> [前端] 执行 npm run build..."
npm run build

# 使用 Vite preview 提供静态页面，方便快速访问
FRONTEND_PORT=4173
echo ">>> [前端] 启动 Vite preview（端口 ${FRONTEND_PORT}，对外暴露）..."
nohup npm run preview -- --host 0.0.0.0 --port "${FRONTEND_PORT}" > "${ROOT_DIR}/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo ">>> [前端] 已启动，PID=${FRONTEND_PID}，日志：${ROOT_DIR}/frontend.log"

#######################################
# 3. 输出访问说明
#######################################
echo ""
echo "========================================"
echo "部署完成（开发 / 测试环境）"
echo ""
echo "后端 API：  http://<服务器IP>:${BACKEND_PORT}"
echo "  - 健康检查：GET /health"
echo "  - 识别接口：POST /api/analyze"
echo ""
echo "前端页面：  http://<服务器IP>:${FRONTEND_PORT}"
echo ""
echo "后台运行日志："
echo "  - 后端：${ROOT_DIR}/backend.log   (uv + FastAPI)"
echo "  - 前端：${ROOT_DIR}/frontend.log  (Vite preview)"
echo "========================================"
echo ""

