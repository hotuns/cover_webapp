#!/usr/bin/env bash

# 快速重启脚本（开发 / 测试用）
# 说明：
# - 先调用 stop.sh 尝试停止已有进程
# - 再调用 deploy_quick.sh 重新启动后端与前端

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> 执行 stop.sh..."
bash "${ROOT_DIR}/stop.sh" || echo ">>> stop.sh 执行出现问题，继续尝试重新部署。"

echo ">>> 执行 deploy_quick.sh..."
bash "${ROOT_DIR}/deploy_quick.sh"

echo ">>> restart.sh 完成。"

