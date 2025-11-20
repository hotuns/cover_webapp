"""
Coverage computation using a RandomForest model (preferred),
with a lightweight green-dominance heuristic fallback when the model is unavailable.

Exposes:
    compute_coverage(input_image_name: str, output_image_name: str) -> tuple[float, str]
"""
import cv2
import numpy as np
import joblib
import warnings
_MODEL_CACHE: tuple[object, str] | None = None
try:
    # For suppressing model version warnings
    from sklearn.base import InconsistentVersionWarning  # type: ignore
except Exception:  # sklearn may not be present during some tooling
    class InconsistentVersionWarning(Warning):
        pass
from config import COVER_RF_MODEL_PATH


def _heuristic_green_ratio_mask(img_bgr):
    """Simple green-dominance heuristic to estimate vegetation mask."""
    g = img_bgr[:, :, 1].astype(np.int32)
    r = img_bgr[:, :, 2].astype(np.int32)
    b = img_bgr[:, :, 0].astype(np.int32)
    mask = (g > r) & (g > b) & (g > 80)
    return mask


def _compute_features_np(img_rgb: np.ndarray) -> np.ndarray:
    """Compute per-pixel features and return NumPy array [N, 9]."""
    r = img_rgb[:, :, 0].astype(np.float32)
    g = img_rgb[:, :, 1].astype(np.float32)
    b = img_rgb[:, :, 2].astype(np.float32)

    epsilon = np.float32(1e-10)
    # Avoid divide-by-zero
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

    # Flatten in row-major order and stack into [N, 9]
    features = np.stack([
        r.flatten(), g.flatten(), b.flatten(),
        rr.flatten(), rg.flatten(), rb.flatten(),
        gr_ratio.flatten(), gb_ratio.flatten(), br_ratio.flatten()
    ], axis=1)
    return features


def _load_rf_model() -> tuple[object, str] | tuple[None, None]:
    """Load RandomForest model from common search locations.

    Returns (model, path) or (None, None) if not found.
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    # Unified priority: config path -> alongside this file -> CWD
    import os
    candidates = [COVER_RF_MODEL_PATH]
    here = os.path.dirname(__file__)
    candidates.append(os.path.join(here, 'random_forest_model.joblib'))
    candidates.append('random_forest_model.joblib')

    for p in candidates:
        try:
            if p and os.path.isfile(p):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=InconsistentVersionWarning)
                    model = joblib.load(p)
                # Try to enable multi-core prediction if supported
                try:
                    import os as _os
                    n_jobs = max(1, (_os.cpu_count() or 1) - 0)
                    # Direct attribute
                    if hasattr(model, 'n_jobs'):
                        setattr(model, 'n_jobs', -1 if n_jobs > 1 else 1)
                    # If it's a pipeline, set on final estimator if available
                    if hasattr(model, 'steps') and isinstance(getattr(model, 'steps'), (list, tuple)):
                        for name, est in model.steps:
                            if hasattr(est, 'n_jobs'):
                                setattr(est, 'n_jobs', -1 if n_jobs > 1 else 1)
                except Exception:
                    pass
                _MODEL_CACHE = (model, p)
                return _MODEL_CACHE
        except Exception:
            # Try next candidate
            continue
    return None, None


def compute_coverage(input_image_name: str, output_image_name: str):
    """
    Compute vegetation coverage mask and ratio using a RandomForest model if available.
    Falls back to a heuristic green-dominance mask when the model is unavailable.

    Args:
        input_image_name: path to the input image file
        output_image_name: path to write the output mask image (PNG/JPG)

    Returns:
        (ratio, output_image_name)
    """
    # Read image (BGR)
    img_bgr = cv2.imread(input_image_name, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise FileNotFoundError(f"Failed to read image: {input_image_name}")

    # Keep original resolution; RF features are per-pixel
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # Try load model
    model, model_path = _load_rf_model()

    try:
        if model is not None:
            X = _compute_features_np(img_rgb)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=InconsistentVersionWarning)
                preds = model.predict(X)

            # Normalize predictions to boolean mask (True for vegetation)
            if hasattr(preds, 'dtype') and np.issubdtype(preds.dtype, np.number):
                veg_mask = preds.reshape(img_rgb.shape[0], img_rgb.shape[1]) > 0.5
            else:
                # Assume string labels like 'veg' / 'non_veg'
                veg_mask = preds.reshape(img_rgb.shape[0], img_rgb.shape[1]) == 'veg'
        else:
            # Fallback heuristic
            veg_mask = _heuristic_green_ratio_mask(img_bgr)
    except Exception:
        # Any model/predict failure: fallback
        veg_mask = _heuristic_green_ratio_mask(img_bgr)

    ratio = float(np.count_nonzero(veg_mask)) / veg_mask.size

    # Write binary mask (0/255)
    mask_img = (veg_mask.astype(np.uint8) * 255)
    cv2.imwrite(output_image_name, mask_img)
    return ratio, output_image_name
