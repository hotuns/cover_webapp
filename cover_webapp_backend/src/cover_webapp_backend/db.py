"""
简单的 SQLite 持久化封装。

说明：
- 使用标准库 sqlite3，避免额外 ORM 依赖；
- 由应用启动时自动创建表结构；
- 每个请求获取独立连接，使用完自动关闭。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional


DB_FILE = Path(__file__).resolve().parent / "data" / "cover_webapp.db"


def init_db() -> None:
    """初始化数据库及基础表结构。"""
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guests (
                id TEXT PRIMARY KEY,
                used_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guest_id TEXT,
                image_path TEXT NOT NULL,
                mask_path TEXT NOT NULL,
                coverage REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (guest_id) REFERENCES guests(id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                analysis_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (user_id, analysis_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """获取一个自动提交并自动关闭的数据库连接。"""
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()


@dataclass
class User:
    """用户实体的简单数据类。"""

    id: int
    phone: str


def get_user_by_token(token: str) -> Optional[User]:
    """根据会话 token 查找用户，找不到时返回 None。"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT u.id, u.phone
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return User(id=int(row["id"]), phone=str(row["phone"]))

