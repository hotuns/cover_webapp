"""
植被盖度识别服务封装。

此模块将原有的 RandomForest 模型 + 绿色占比启发式逻辑封装为一个
compute_coverage 函数，供 Web 接口调用。
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Tuple

import cv2
import joblib
import numpy as np

try:
    # sklearn 可能不存在，因此导入放在 try 块中
    from sklearn.base import InconsistentVersionWarning  # type: ignore
except Exception:  # pragma: no cover - 仅兼容性兜底
    class InconsistentVersionWarning(Warning):
        """在未安装 sklearn 时的占位告警类型。"""

        pass


_MODEL_CACHE: Tuple[object, str] | None = None


def _default_model_candidates() -> list[str]:
    """推断模型文件可能存在的路径列表。"""
    candidates: list[str] = []
    here = Path(__file__).resolve().parent

    # 1）优先放在当前包目录下
    candidates.append(str(here / "random_forest_model.joblib"))
    # 2）兼容旧结构：../server/random_forest_model.joblib
    candidates.append(str(here.parent.parent / "server" / "random_forest_model.joblib"))
    # 3）当前工作目录
    candidates.append("random_forest_model.joblib")
    return candidates


def _heuristic_green_ratio_mask(img_bgr: np.ndarray) -> np.ndarray:
    """简单绿色通道占优启发式，返回植被掩膜。

    逻辑：
    - G 通道同时大于 R、B
    - G 通道强度大于 80
    """
    g = img_bgr[:, :, 1].astype(np.int32)
    r = img_bgr[:, :, 2].astype(np.int32)
    b = img_bgr[:, :, 0].astype(np.int32)
    mask = (g > r) & (g > b) & (g > 80)
    return mask


def _compute_features_np(img_rgb: np.ndarray) -> np.ndarray:
    """按像素计算 9 维特征，返回形状为 [N, 9] 的矩阵。"""
    r = img_rgb[:, :, 0].astype(np.float32)
    g = img_rgb[:, :, 1].astype(np.float32)
    b = img_rgb[:, :, 2].astype(np.float32)

    epsilon = np.float32(1e-10)
    r = np.where(r == 0, epsilon, r)
    g = np.where(g == 0, epsilon, g)
    b = np.where(b == 0, epsilon, b)

    s = r + g + b
    s = np.where(s == 0, epsilon, s)

    rr = 3.0 * r / s
    rg = 3.0 * g / s
    rb = 3.0 * b / s
    gr_ratio = g / r
    gb_ratio = g / b
    br_ratio = b / r

    features = np.stack(
        [
            r.flatten(),
            g.flatten(),
            b.flatten(),
            rr.flatten(),
            rg.flatten(),
            rb.flatten(),
            gr_ratio.flatten(),
            gb_ratio.flatten(),
            br_ratio.flatten(),
        ],
        axis=1,
    )
    return features


def _load_rf_model() -> Tuple[object, str] | Tuple[None, None]:
    """尝试加载 RandomForest 模型，返回 (模型对象, 路径) 或 (None, None)。"""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    for path in _default_model_candidates():
        try:
            if path and os.path.isfile(path):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=InconsistentVersionWarning)
                    model = joblib.load(path)

                # 尝试启用多核预测
                try:
                    n_jobs = max(1, (os.cpu_count() or 1) - 0)
                    if hasattr(model, "n_jobs"):
                        setattr(model, "n_jobs", -1 if n_jobs > 1 else 1)
                    if hasattr(model, "steps") and isinstance(getattr(model, "steps"), (list, tuple)):
                        for _, est in model.steps:
                            if hasattr(est, "n_jobs"):
                                setattr(est, "n_jobs", -1 if n_jobs > 1 else 1)
                except Exception:
                    # 并行设置失败不影响主流程
                    pass

                _MODEL_CACHE = (model, path)
                return _MODEL_CACHE
        except Exception:
            # 单个候选失败时继续尝试下一个
            continue

    return None, None


def compute_coverage(input_image_name: str, output_image_name: str) -> tuple[float, str]:
    """计算植被掩膜与盖度比例。

    优先使用 RandomForest 模型；模型不可用或预测失败时退回到启发式方案。
    返回值为 (覆盖比例, 掩膜图像实际写入路径)。
    """
    img_bgr = cv2.imread(input_image_name, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise FileNotFoundError(f"无法读取输入图像: {input_image_name}")

    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    model, _model_path = _load_rf_model()
    try:
        if model is not None:
            X = _compute_features_np(img_rgb)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=InconsistentVersionWarning)
                preds = model.predict(X)

            if hasattr(preds, "dtype") and np.issubdtype(preds.dtype, np.number):
                veg_mask = preds.reshape(img_rgb.shape[0], img_rgb.shape[1]) > 0.5
            else:
                veg_mask = preds.reshape(img_rgb.shape[0], img_rgb.shape[1]) == "veg"
        else:
            veg_mask = _heuristic_green_ratio_mask(img_bgr)
    except Exception:
        veg_mask = _heuristic_green_ratio_mask(img_bgr)

    ratio = float(np.count_nonzero(veg_mask)) / veg_mask.size

    mask_img = veg_mask.astype(np.uint8) * 255
    out_path = Path(output_image_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), mask_img)
    return ratio, str(out_path)


