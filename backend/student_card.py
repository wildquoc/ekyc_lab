"""Đọc mã vạch hàng ngang trên thẻ sinh viên.

Họ tên không được OCR ở bước này. Số CCCD và họ tên đã có từ bước căn cước.
"""
from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence, Tuple

import cv2
import numpy as np

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]{3,31}")
_ZXING_FORMATS = None


def normalize_student_id(raw: str) -> Optional[str]:
    """Lấy mã sinh viên từ chuỗi mã vạch. Bỏ URL và khoảng trắng."""
    text = (raw or "").strip()
    if not text:
        return None
    if "/" in text:
        text = text.rstrip("/").split("/")[-1]
    text = re.sub(r"\s+", "", text)
    match = _ID_RE.search(text)
    if not match:
        return None
    return match.group(0).upper()


def _as_point_sets(points: Any, count: int) -> List[Optional[np.ndarray]]:
    if points is None:
        return [None] * count
    arr = np.asarray(points)
    if arr.size == 0:
        return [None] * count
    if arr.ndim == 2 and count == 1:
        return [arr.reshape(-1, 2)]
    if arr.ndim >= 3:
        return [arr[i].reshape(-1, 2) for i in range(min(count, arr.shape[0]))]
    return [None] * count


def _is_horizontal(pts: Optional[np.ndarray]) -> bool:
    if pts is None or len(pts) < 2:
        return True
    width = float(pts[:, 0].max() - pts[:, 0].min())
    height = float(pts[:, 1].max() - pts[:, 1].min())
    return width >= height * 1.15


def _as_texts(info: Any) -> List[str]:
    if info is None:
        return []
    if isinstance(info, str):
        return [info] if info.strip() else []
    if isinstance(info, (bytes, bytearray)):
        text = info.decode("utf-8", "ignore").strip()
        return [text] if text else []
    arr = np.asarray(info)
    if arr.dtype != object and arr.ndim >= 2 and np.issubdtype(arr.dtype, np.number):
        return []
    try:
        items = list(info)
    except TypeError:
        text = str(info).strip()
        return [text] if text else []
    out: List[str] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, bytes):
            item = item.decode("utf-8", "ignore")
        text = str(item).strip()
        if text and not text.startswith("[") and not text.startswith("("):
            out.append(text)
    return out


def _decode_call(detector: Any, image: np.ndarray) -> Tuple[Sequence[str], Any]:
    """Chuẩn hoá mọi kiểu trả về của OpenCV 4/5 và detector giả trong test."""
    if detector is None:
        return [], None
    if hasattr(detector, "detectAndDecodeWithType"):
        try:
            parsed = _parse_detector_result(detector.detectAndDecodeWithType(image))
            if parsed[0]:
                return parsed
        except Exception:
            pass
    try:
        result = detector.detectAndDecode(image)
    except Exception:
        return [], None
    return _parse_detector_result(result)


def _parse_detector_result(result: Any) -> Tuple[Sequence[str], Any]:
    if result is None:
        return [], None
    if not isinstance(result, tuple):
        return _as_texts(result), None
    count = len(result)
    if count == 4:
        first, info, _types, points = result
        texts = _as_texts(info) or (_as_texts(first) if isinstance(first, str) else [])
        return texts, points
    if count == 3:
        first, second, third = result
        # OpenCV 5 detectAndDecode: (decoded_string, points, straight_code)
        if isinstance(first, str):
            return ([first] if first.strip() else []), second
        return _as_texts(second), third
    if count == 2:
        first, second = result
        if isinstance(first, str):
            return ([first] if first.strip() else []), second
        return _as_texts(first), second
    return [], None


def _zxing_formats():
    global _ZXING_FORMATS
    if _ZXING_FORMATS is None:
        import zxingcpp

        _ZXING_FORMATS = zxingcpp.AllLinear
    return _ZXING_FORMATS


def _points_from_zxing(position: Any) -> Optional[np.ndarray]:
    if position is None:
        return None
    try:
        corners = (
            position.top_left,
            position.top_right,
            position.bottom_right,
            position.bottom_left,
        )
        return np.array([[float(p.x), float(p.y)] for p in corners], dtype=np.float32)
    except Exception:
        return None


def _decode_zxing(image: np.ndarray) -> Tuple[List[str], List[Optional[np.ndarray]]]:
    try:
        import zxingcpp
    except ImportError:
        return [], []
    try:
        hits = zxingcpp.read_barcodes(
            image,
            formats=_zxing_formats(),
            try_rotate=True,
            try_downscale=True,
            try_invert=True,
        )
    except Exception:
        return [], []
    texts: List[str] = []
    points: List[Optional[np.ndarray]] = []
    for hit in hits or []:
        text = str(getattr(hit, "text", "") or "").strip()
        if not text:
            continue
        texts.append(text)
        points.append(_points_from_zxing(getattr(hit, "position", None)))
    return texts, points


def _barcode_views(image_bgr: np.ndarray) -> List[np.ndarray]:
    """Khung giữa (đúng overlay) rồi nửa dưới — mã vạch thẻ SV thường nằm đáy thẻ."""
    height, width = image_bgr.shape[:2]
    views: List[np.ndarray] = [image_bgr]
    band_h = max(24, int(round(height * 0.36)))
    y0 = max(0, (height - band_h) // 2)
    mid = image_bgr[y0 : y0 + band_h, :]
    if mid.size and mid.shape[0] >= 24:
        views.append(mid)
    bottom = image_bgr[int(height * 0.52) :, :]
    if bottom.size and bottom.shape[0] >= 24:
        views.append(bottom)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    if gray.size:
        views.append(gray)
    return views


def _collect_hits(
    texts: Sequence[str],
    points: Any,
) -> Tuple[List[str], int]:
    sets = _as_point_sets(points, len(texts)) if not isinstance(points, list) else points
    if len(sets) < len(texts):
        sets = list(sets) + [None] * (len(texts) - len(sets))
    horizontal: List[str] = []
    vertical = 0
    for text, pts in zip(texts, sets):
        student_id = normalize_student_id(text)
        if not student_id:
            continue
        if _is_horizontal(pts):
            horizontal.append(student_id)
        else:
            vertical += 1
    return horizontal, vertical


def decode_student_barcode(image_bgr: np.ndarray, detector: Any = None) -> dict:
    """Tìm mã vạch nằm ngang và trả mã sinh viên.

    ``detector`` chỉ dùng khi kiểm thử. Mặc định: ZXing, rồi OpenCV nếu còn.
    """
    empty = {
        "found": False,
        "student_id": None,
        "guidance": "Đưa mã vạch ngang trên thẻ sinh viên vào khung",
        "color": "cyan",
    }
    if image_bgr is None or image_bgr.size == 0:
        return empty

    horizontal: List[str] = []
    vertical = 0

    if detector is not None:
        texts, points = _decode_call(detector, image_bgr)
        horizontal, vertical = _collect_hits(texts, points)
    else:
        for view in _barcode_views(image_bgr):
            texts, pts_list = _decode_zxing(view)
            found, vert = _collect_hits(texts, pts_list)
            horizontal.extend(found)
            vertical += vert
            if horizontal:
                break
        if not horizontal:
            barcode_mod = getattr(cv2, "barcode", None)
            opencv_det = detector
            if opencv_det is None and barcode_mod is not None and hasattr(barcode_mod, "BarcodeDetector"):
                try:
                    opencv_det = barcode_mod.BarcodeDetector()
                except Exception as exc:
                    empty["guidance"] = f"Không mở được bộ đọc mã vạch: {exc}"
                    empty["color"] = "red"
                    opencv_det = None
            if opencv_det is not None:
                try:
                    texts, points = _decode_call(opencv_det, image_bgr)
                    found, vert = _collect_hits(texts, points)
                    horizontal.extend(found)
                    vertical += vert
                except Exception as exc:
                    empty["guidance"] = f"Lỗi đọc mã vạch: {exc}"
                    empty["color"] = "red"

    if horizontal:
        return {
            "found": True,
            "student_id": horizontal[0],
            "guidance": "Đã đọc mã sinh viên",
            "color": "green",
        }
    if vertical:
        empty["guidance"] = "Xoay thẻ để mã vạch nằm ngang trong khung"
        empty["color"] = "yellow"
    return empty
