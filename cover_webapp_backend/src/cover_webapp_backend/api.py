"""
FastAPI 应用定义与 HTTP 接口。

主要功能：
- 手机号注册/登录，返回简单 token；
- 游客与登录用户统一使用图片识别接口；
- 游客限制为最多 3 次识别，登录后不限次；
- 单次请求仅支持上传一张图片。
"""

from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, constr

from .coverage_service import compute_coverage
from .db import DB_FILE, get_conn, get_user_by_token, init_db, User


class LoginRequest(BaseModel):
    """登录/注册请求体。"""

    phone: constr(strip_whitespace=True, min_length=3, max_length=32)  # 简单长度约束


class LoginResponse(BaseModel):
    """登录/注册响应体。"""

    token: str
    phone: str
    is_new: bool


class AnalyzeResponse(BaseModel):
    """图片识别响应体。"""

    id: int
    coverage: float
    mask_url: str
    guest_id: Optional[str] = None
    guest_used: Optional[int] = None
    guest_limit: Optional[int] = None


class SavedAnalysisItem(BaseModel):
    """已保存识别记录条目。"""

    id: int
    coverage: float
    created_at: str
    mask_url: str
    thumb_url: str


def _now_str() -> str:
    """当前时间的 ISO8601 字符串表示。"""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _create_thumbnail(origin_path: Path, static_dir: Path, max_size: int = 320) -> Optional[Path]:
    """为原始图片生成缩略图文件并返回路径（失败时返回 None）。

    实现说明：
    - 优先使用 opencv 缩放生成较小图片；
    - 若 opencv 不可用或读图失败，则退化为直接复制原图；
    - 缩略图统一存放在 static/thumbs 目录下，文件名沿用原图文件名。
    """
    thumbs_dir = static_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cv2  # type: ignore

        img = cv2.imread(str(origin_path))
        if img is None:
            raise RuntimeError("无法读取原始图片")
        h, w = img.shape[:2]
        if h <= 0 or w <= 0:
            raise RuntimeError("图像尺寸异常")

        scale = max(h, w) / float(max_size)
        if scale < 1.0:
            scale = 1.0
        new_w = max(1, int(w / scale))
        new_h = max(1, int(h / scale))

        thumb_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        out_path = thumbs_dir / origin_path.name
        cv2.imwrite(str(out_path), thumb_img)
        return out_path
    except Exception:
        try:
            out_path = thumbs_dir / origin_path.name
            if origin_path.is_file():
                out_path.write_bytes(origin_path.read_bytes())
                return out_path
        except Exception:
            return None
    return None


def create_app() -> FastAPI:
    """工厂函数，用于创建 FastAPI 应用实例。"""
    init_db()

    app = FastAPI(title="Plant Coverage Web API", version="0.1.0")

    # 允许本地开发前端访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = Path(__file__).resolve().parent / "data" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    # 预创建用于掩膜与缩略图的子目录
    (static_dir / "masks").mkdir(parents=True, exist_ok=True)
    (static_dir / "thumbs").mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.post("/api/auth/login", response_model=LoginResponse)
    async def login(payload: LoginRequest) -> LoginResponse:
        """手机号登录/注册接口。"""
        phone = payload.phone
        now = _now_str()
        is_new = False

        with get_conn() as conn:
            cur = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,))
            row = cur.fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO users (phone, created_at) VALUES (?, ?)",
                    (phone, now),
                )
                cur = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,))
                row = cur.fetchone()
                is_new = True

            user_id = int(row["id"])
            token = secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO sessions (user_id, token, created_at) VALUES (?, ?, ?)",
                (user_id, token, now),
            )

        return LoginResponse(token=token, phone=phone, is_new=is_new)

    async def current_user(request: Request) -> Optional[User]:
        """从 Authorization 头中解析当前登录用户（如果存在）。"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            return None
        token = auth_header[len(prefix) :].strip()
        if not token:
            return None
        return get_user_by_token(token)

    @app.get("/api/me")
    async def me(user: Optional[User] = Depends(current_user)):
        """查询当前登录状态，未登录时返回匿名信息。"""
        if user is None:
            return {"authenticated": False}
        return {"authenticated": True, "phone": user.phone}

    async def require_user(user: Optional[User] = Depends(current_user)) -> User:
        """强制要求已登录用户的依赖。"""
        if user is None:
            raise HTTPException(status_code=401, detail="请先登录后再执行该操作。")
        return user

    @app.post("/api/analyze", response_model=AnalyzeResponse)
    async def analyze(
        request: Request,
        file: UploadFile = File(...),
        guest_id: Optional[str] = None,
        user: Optional[User] = Depends(current_user),
    ) -> AnalyzeResponse:
        """单张图片识别接口。

        规则：
        - 已登录用户：不限次数；
        - 游客：绑定 guest_id，最多 3 次。
        """
        uploads_root = Path(__file__).resolve().parent / "data" / "uploads"
        origin_dir = uploads_root / "origin"
        mask_dir = uploads_root / "mask"
        origin_dir.mkdir(parents=True, exist_ok=True)
        mask_dir.mkdir(parents=True, exist_ok=True)

        new_guest_id: Optional[str] = None
        guest_used: Optional[int] = None
        guest_limit: Optional[int] = None

        with get_conn() as conn:
            if user is None:
                # 游客模式：按 guest_id 限制 3 次
                if not guest_id:
                    new_guest_id = secrets.token_urlsafe(16)
                    guest_id = new_guest_id
                    conn.execute(
                        "INSERT OR IGNORE INTO guests (id, used_count, created_at) VALUES (?, 0, ?)",
                        (guest_id, _now_str()),
                    )

                cur = conn.execute("SELECT used_count FROM guests WHERE id = ?", (guest_id,))
                row = cur.fetchone()
                if row is None:
                    new_guest_id = guest_id
                    conn.execute(
                        "INSERT INTO guests (id, used_count, created_at) VALUES (?, 0, ?)",
                        (guest_id, _now_str()),
                    )
                    used_count = 0
                else:
                    used_count = int(row["used_count"])

                guest_limit = 3
                guest_used = used_count
                if used_count >= guest_limit:
                    raise HTTPException(
                        status_code=403,
                        detail="未登录用户最多可识别 3 次，请登录后继续使用。",
                    )
            # 已登录用户则无需限次

        # 将上传文件保存到磁盘
        suffix = ""
        if file.filename:
            suffix = Path(file.filename).suffix
        if not suffix:
            suffix = ".jpg"
        file_id = secrets.token_hex(16)
        origin_path = origin_dir / f"{file_id}{suffix}"
        mask_path = mask_dir / f"{file_id}.png"

        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="上传文件不能为空。")
        origin_path.write_bytes(data)

        # 调用识别逻辑
        try:
            coverage, real_mask_path = compute_coverage(str(origin_path), str(mask_path))
        except FileNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:  # pragma: no cover - 真实服务中记录日志
            raise HTTPException(status_code=500, detail="服务器处理图片时发生错误。") from e

        # 记录结果并更新游客计数
        analysis_id: int
        with get_conn() as conn:
            if user is None and guest_id is not None:
                conn.execute(
                    "UPDATE guests SET used_count = used_count + 1 WHERE id = ?",
                    (guest_id,),
                )
                cur = conn.execute("SELECT used_count FROM guests WHERE id = ?", (guest_id,))
                row = cur.fetchone()
                if row:
                    guest_used = int(row["used_count"])

            cur = conn.execute(
                """
                INSERT INTO analyses (user_id, guest_id, image_path, mask_path, coverage, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user.id if user is not None else None,
                    guest_id,
                    str(origin_path),
                    str(real_mask_path),
                    float(coverage),
                    _now_str(),
                ),
            )
            analysis_id = int(cur.lastrowid)

        # 构造前端可使用的掩膜图 URL（相对 /static）
        static_dir = Path(__file__).resolve().parent / "data" / "static"
        static_masks = static_dir / "masks"
        static_masks.mkdir(parents=True, exist_ok=True)
        # 将掩膜文件复制到静态目录
        mask_target = static_masks / Path(real_mask_path).name
        if mask_target != Path(real_mask_path):
            mask_target.write_bytes(Path(real_mask_path).read_bytes())

        # 为原始图生成缩略图（最佳努力）
        _create_thumbnail(origin_path, static_dir)

        mask_url = f"/static/masks/{mask_target.name}"

        return AnalyzeResponse(
            id=analysis_id,
            coverage=float(coverage),
            mask_url=mask_url,
            guest_id=guest_id if user is None else None,
            guest_used=guest_used,
            guest_limit=guest_limit,
        )

    @app.post("/api/analyses/{analysis_id}/save")
    async def save_analysis(
        analysis_id: int,
        user: User = Depends(require_user),
    ):
        """将指定识别结果标记为当前用户的已保存记录。"""
        with get_conn() as conn:
            cur = conn.execute(
                "SELECT id, coverage, mask_path, image_path, created_at FROM analyses WHERE id = ?",
                (analysis_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="识别记录不存在，无法保存。")

            conn.execute(
                """
                INSERT OR IGNORE INTO saved_analyses (user_id, analysis_id, created_at)
                VALUES (?, ?, ?)
                """,
                (user.id, int(row["id"]), _now_str()),
            )

        return {"status": "ok"}

    @app.get("/api/analyses/saved", response_model=List[SavedAnalysisItem])
    async def list_saved_analyses(
        limit: int = 20,
        user: User = Depends(require_user),
    ) -> List[SavedAnalysisItem]:
        """列出当前登录用户已保存的识别记录。"""
        limit = max(1, min(limit, 100))
        static_dir = Path(__file__).resolve().parent / "data" / "static"
        static_masks = static_dir / "masks"
        static_thumbs = static_dir / "thumbs"
        static_thumbs.mkdir(parents=True, exist_ok=True)

        items: List[SavedAnalysisItem] = []
        with get_conn() as conn:
            cur = conn.execute(
                """
                SELECT a.id, a.coverage, a.mask_path, a.image_path, a.created_at
                FROM saved_analyses sa
                JOIN analyses a ON a.id = sa.analysis_id
                WHERE sa.user_id = ?
                ORDER BY sa.created_at DESC
                LIMIT ?
                """,
                (user.id, limit),
            )
            rows = cur.fetchall()

        for row in rows:
            mask_name = Path(row["mask_path"]).name
            mask_url = f"/static/masks/{mask_name}"
            origin_path = Path(row["image_path"])
            # 尝试确保缩略图存在
            _create_thumbnail(origin_path, static_dir)
            thumb_name = origin_path.name
            thumb_url = f"/static/thumbs/{thumb_name}"
            items.append(
                SavedAnalysisItem(
                    id=int(row["id"]),
                    coverage=float(row["coverage"]),
                    created_at=str(row["created_at"]),
                    mask_url=mask_url,
                    thumb_url=thumb_url,
                )
            )

        return items

    @app.get("/health")
    async def health() -> JSONResponse:
        """健康检查接口。"""
        exists = DB_FILE.exists()
        return JSONResponse({"status": "ok", "db_exists": exists})

    return app


# 全局 app 供 uvicorn 引用
app = create_app()
