[2025-11-20] 本地测试记录（由 Codex 生成）

1. Python 后端语法检查
   - 命令：cd cover_webapp_backend && python -m compileall src
   - 结果：成功，所有模块编译通过（无语法错误）。

2. Python 单元测试（unittest）
   - 命令：cd /home/hotuns/python-projects/cover_webapp && PYTHONPATH=cover_webapp_backend/src python -m unittest discover -s cover_webapp_backend/tests
   - 结果：通过（2 个用例，其中 1 个跳过：覆盖计算模块在缺少 cv2/joblib 依赖时自动跳过导入测试）。

3. 前端 Vitest 测试
   - 说明：当前环境未安装 Node/Vite 依赖，未实际执行 `npm install` / `npm test`。
   - 风险评估：前端仅包含简单 smoke 测试（加法校验），结构正确后在真实环境安装依赖并执行 `npm run test` 即可验证。

后续建议：
- 在联网且具备 Node 环境的机器上执行：
  - cd webapp && npm install && npm run test
- 在具备 Python 依赖（fastapi、opencv-python、joblib 等）并安装 uv 的环境中执行：
  - cd cover_webapp_backend && UV_CACHE_DIR=.uv-cache uv sync
  - UV_CACHE_DIR=.uv-cache uv run cover-webapp-backend
