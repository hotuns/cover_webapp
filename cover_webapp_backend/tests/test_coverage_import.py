"""
覆盖计算模块的导入测试。

说明：
- 由于依赖 cv2 / joblib 等外部库，本测试在库缺失时会自动跳过；
- 主要用于在依赖已安装的环境中快速验证模块可导入。
"""

import unittest

try:
    from cover_webapp_backend import coverage_service as _coverage_service
except Exception:  # pragma: no cover - 在依赖缺失时触发
    _coverage_service = None


class TestCoverageImport(unittest.TestCase):
    """覆盖计算模块的导入冒烟测试。"""

    def test_module_importable_or_skipped(self) -> None:
        """若依赖齐全，应能成功导入模块。"""
        if _coverage_service is None:
            self.skipTest("cv2/joblib 等依赖未安装，跳过覆盖模块导入测试")
        # 模块存在时，至少应暴露 compute_coverage 函数
        self.assertTrue(
            hasattr(_coverage_service, "compute_coverage"),
            "coverage_service 中缺少 compute_coverage 函数",
        )


if __name__ == "__main__":
    unittest.main()

