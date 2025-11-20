"""
数据库初始化的基础单元测试。

验证内容：
- init_db 可正常执行；
- 数据库文件确实被创建。
"""

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_db_module():
    """通过文件路径加载 db 模块，避免依赖包入口导入 FastAPI 等第三方库。"""
    root = Path(__file__).resolve().parents[1]
    db_path = root / "src" / "cover_webapp_backend" / "db.py"
    module_name = "cover_webapp_backend_db"
    spec = importlib.util.spec_from_file_location(module_name, db_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclass 装饰器需要在 sys.modules 中找到模块
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


class TestDbInit(unittest.TestCase):
    """针对 SQLite 初始化的冒烟测试。"""

    def test_init_db_creates_file(self) -> None:
        """运行 init_db 后应生成数据库文件。"""
        db = _load_db_module()
        db_file: Path = db.DB_FILE
        if db_file.exists():
            db_file.unlink()
        db.init_db()
        self.assertTrue(db_file.exists(), "数据库文件未创建")

        # 验证核心表是否存在（包含 saved_analyses）
        import sqlite3

        conn = sqlite3.connect(db_file)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users','analyses','saved_analyses')"
            )
            names = {row[0] for row in cur.fetchall()}
            self.assertIn("users", names)
            self.assertIn("analyses", names)
            self.assertIn("saved_analyses", names)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
