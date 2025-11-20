[2025-11-20] 初始化记录：阅读 server/coverage.py 与 plantcv_server.py；使用 UV_CACHE_DIR 初始化 uv 项目 cover_webapp_backend。
[2025-11-20] 更新 cover_webapp_backend/pyproject.toml：添加 FastAPI、Uvicorn、图像识别相关依赖。
[2025-11-20] 新增后端代码：coverage_service.py、db.py、api.py，支持 FastAPI 接口与 SQLite 存储、游客 3 次限额逻辑。
[2025-11-20] 新增 webapp/ Vite+Vue3 PWA 前端骨架，支持手机上传、游客限次与登录调用后端 API。
[2025-11-20] 为后端新增 unittest 测试（数据库初始化与覆盖模块导入），并通过 tests/__init__.py 注入 src 路径。
[2025-11-20] 优化前端样式：重构 webapp/src/App.vue 布局为卡片化专业风格（渐变背景、两列布局、统一按钮与标签样式）。
[2025-11-20] 调整前端布局：将账号状态与登录入口移动到左上角，并新增内嵌手机号登录表单，突出上传识别卡片为页面主体。
[2025-11-20] 新增识别记录保存功能：后端支持 /api/analyses/{id}/save 与 /api/analyses/saved，前端结果卡片提供“保存本次记录”和历史记录列表，登录改为全屏居中 Modal。
[2025-11-20] 保存记录增强：后端为每次识别生成原图缩略图（static/thumbs），/api/analyses/saved 返回 thumb_url；前端历史列表展示小预览图，并在点击记录时同时展示该缩略图。
[2025-11-20] 调整缩略图样式：为历史记录中的 .history-thumb 设置 56x56 固定尺寸和圆角边框，避免缩略图过大影响列表布局。
[2025-11-20] 新增一键部署脚本 deploy_quick.sh：使用 uv 启动后端、使用 Vite preview 启动前端，便于在服务器上快速跑通。
