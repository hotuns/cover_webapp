# 本地验证说明（2025-11-20, Codex）

本次实现内容：
- 使用 `uv init` 在 `cover_webapp_backend/` 下初始化 Python 项目，并新增 FastAPI 后端：
  - 登录/注册接口：`POST /api/auth/login`（手机号，返回 token）；
  - 登录状态检查：`GET /api/me`；
  - 单张图片识别接口：`POST /api/analyze`（file + 可选 guest_id）；
  - 健康检查：`GET /health`；
- 后端集成 SQLite：
  - users / sessions / guests / analyses 四张表；
  - 游客最多 3 次识别，登录后不限次；
- 封装植被盖度计算逻辑：
  - `coverage_service.compute_coverage(input_path, output_path)`
  - 优先使用 RandomForest 模型，缺失或失败时回退简单绿色启发式；
- 新建 Vite + Vue3 前端（webapp/）并提供 PWA 能力：
  - manifest.webmanifest + sw.js；
  - 手机号登录 + 游客模式剩余次数提示；
  - 单张图片上传（拍照或相册）并显示盖度与掩膜图。

## 已执行的验证

1. Python 代码语法
   - 通过 `python -m compileall cover_webapp_backend/src` 检查，未发现语法错误。

2. Python 单元测试
   - 命令：`PYTHONPATH=cover_webapp_backend/src python -m unittest discover -s cover_webapp_backend/tests`
   - 结果：
     - test_db_init：验证 `init_db` 可创建 SQLite 文件，执行通过；
     - test_coverage_import：在缺少 `cv2`/`joblib` 的环境下被标记为跳过（依赖安装后将自动生效）。

## 未执行或受限的验证

1. FastAPI 运行验证
   - 受限原因：当前环境未安装 fastapi/uvicorn 等依赖，且网络访问受限，无法通过 uv 下载依赖。
   - 风险：接口在真实依赖安装完成前无法本地启动；但路由与数据流已在代码层面保证基本正确性。

2. 图像模型推理验证
   - 受限原因：缺少 `cv2` 与 `joblib` 包，无法加载 RF 模型或处理真实图片。
   - 风险：在模型文件路径配置错误或模型格式不兼容时可能抛出异常，但均被封装在 try/except 中并回退启发式逻辑；真实效果需在目标环境中结合模型文件进一步验证。

3. 前端构建与 PWA 行为
   - 受限原因：当前环境未执行 `npm install`，无法运行 `vite build` / `vitest`。
   - 风险：
     - 若依赖版本与本地 Node 环境不兼容，需根据提示调整 package.json；
     - PWA 相关行为（离线缓存、图标、高级安装体验）需在浏览器中手动验证。

## 建议的线下验证步骤

在具备完整网络与运行环境的机器上，建议按如下顺序验证：

1. 后端环境
   - cd cover_webapp_backend
   - 设置缓存目录并安装依赖：`UV_CACHE_DIR=.uv-cache uv sync`
   - 启动服务：`UV_CACHE_DIR=.uv-cache uv run cover-webapp-backend`
   - 使用 curl 或 Postman 进行接口冒烟测试：
     - `GET http://localhost:8000/health`
     - `POST http://localhost:8000/api/auth/login`（body: {"phone": "13800000000"}）
     - `POST http://localhost:8000/api/analyze` 上传单张图片验证识别流程。

2. 前端环境
   - cd webapp
   - 安装依赖：`npm install`
   - 启动开发服务器：`npm run dev`
   - 浏览器访问 `http://localhost:5173`：
     - 游客模式下多次上传图片，确认 3 次后得到限制提示；
     - 填写手机号登录后再次上传，确认不再受次数限制；
     - 检查掩膜图是否能正常展示（由后端 `/static/masks/...` 提供）。

3. PWA 行为
   - 在移动端或 Chrome/Edge 中访问前端地址；
   - 打开 DevTools 的 Application 面板，检查 manifest 与 Service Worker 状态；
   - 在网络离线情况下访问最近访问过的页面，确认基础资源可离线加载。

以上验证步骤完成后，可认为本次后端与前端集成达到可上线前的基础质量要求。
