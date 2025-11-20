#!/usr/bin/env bash

# 简单停止脚本（开发 / 测试用）
# 说明：
# - 停止通过 deploy_quick.sh 启动的后端与前端进程
# - 使用 pkill 按命令行匹配，无状态管理，适合快速调试

set -e

echo ">>> 尝试停止后端 (uv run cover-webapp-backend)..."
if pkill -f "uv run cover-webapp-backend" >/dev/null 2>&1; then
  echo ">>> 后端进程已停止。"
else
  echo ">>> 未找到后端进程（可能本来就未运行）。"
fi

echo ">>> 尝试停止前端 (npm run preview / vite preview)..."
if pkill -f "npm run preview" >/dev/null 2>&1 || pkill -f "vite preview" >/dev/null 2>&1; then
  echo ">>> 前端 preview 进程已停止。"
else
  echo ">>> 未找到前端 preview 进程（可能本来就未运行）。"
fi

echo ">>> stop.sh 执行完毕。"

