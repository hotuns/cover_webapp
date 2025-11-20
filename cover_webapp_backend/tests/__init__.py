"""
测试包初始化。

用途：
- 将 src 目录加入 sys.path，便于使用 python -m unittest 直接运行测试；
- 不依赖 uv 特定的运行方式。
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
src_dir = root / "src"
if str(src_dir) not in sys.path:
  sys.path.insert(0, str(src_dir))

