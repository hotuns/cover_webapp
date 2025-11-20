"""
基于 FastAPI 的植被盖度识别后端入口。

提供命令：
    uv run cover-webapp-backend
用于启动 HTTP 服务。
"""

from .api import app  # noqa: F401


def main() -> None:
    """命令行入口，启动 Uvicorn 服务。"""
    import uvicorn

    uvicorn.run(
        "cover_webapp_backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
