"""Kiểm tra đọc mã sinh viên từ mã vạch, không cần webcam."""
from __future__ import annotations

import numpy as np

from student_card import decode_student_barcode, normalize_student_id

_CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112",
]


def _code128_image(data: str, module: int = 3, bar_h: int = 120) -> np.ndarray:
    codes = [104] + [ord(ch) - 32 for ch in data]
    checksum = 104
    for index, code in enumerate(codes[1:], 1):
        checksum += index * code
    codes += [checksum % 103, 106]
    widths: list[int] = []
    for code in codes:
        widths.extend(int(ch) for ch in _CODE128_PATTERNS[code])
    quiet = 24
    width = quiet * 2 + sum(widths) * module
    image = np.full((bar_h + 48, width, 3), 255, dtype=np.uint8)
    x = quiet
    black = True
    for run in widths:
        px = run * module
        if black:
            image[24 : 24 + bar_h, x : x + px] = 0
        x += px
        black = not black
    return image


def test_normalize_student_id_strips_url_and_spaces():
    assert normalize_student_id("  se170123 ") == "SE170123"
    assert normalize_student_id("https://school.edu/id/SV-2048") == "SV-2048"
    assert normalize_student_id("") is None
    assert normalize_student_id("???") is None


class _FakeDetector:
    def __init__(self, texts, points):
        self.texts = texts
        self.points = points

    def detectAndDecode(self, image):
        return True, self.texts, ["CODE_128"] * len(self.texts), self.points


class _OpenCv5Detector:
    def __init__(self, text, points):
        self.text = text
        self.points = points

    def detectAndDecode(self, image):
        return self.text, self.points, None


def test_decode_prefers_horizontal_barcode():
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    vertical = np.array([[10, 10], [30, 10], [30, 180], [10, 180]], dtype=np.float32)
    horizontal = np.array([[40, 80], [360, 80], [360, 120], [40, 120]], dtype=np.float32)
    detector = _FakeDetector(
        ["VERTICAL99", "SE170999"],
        np.stack([vertical, horizontal]),
    )
    result = decode_student_barcode(image, detector=detector)
    assert result["found"] is True
    assert result["student_id"] == "SE170999"


def test_decode_rejects_vertical_only():
    image = np.zeros((200, 80, 3), dtype=np.uint8)
    vertical = np.array([[10, 10], [40, 10], [40, 180], [10, 180]], dtype=np.float32)
    detector = _FakeDetector(["SE170123"], vertical.reshape(1, 4, 2))
    result = decode_student_barcode(image, detector=detector)
    assert result["found"] is False
    assert "ngang" in result["guidance"].lower()


def test_opencv5_detect_and_decode_tuple():
    image = np.zeros((120, 360, 3), dtype=np.uint8)
    points = np.array([[20, 40], [340, 40], [340, 80], [20, 80]], dtype=np.float32)
    detector = _OpenCv5Detector("SE170999", points)
    result = decode_student_barcode(image, detector=detector)
    assert result["found"] is True
    assert result["student_id"] == "SE170999"


def test_zxing_reads_code128_student_id():
    barcode = _code128_image("SE170999")
    scene = np.full((420, 720, 3), 210, dtype=np.uint8)
    bh, bw = barcode.shape[:2]
    scale = min(560 / bw, 120 / bh)
    bar = np.zeros((max(1, int(bh * scale)), max(1, int(bw * scale)), 3), dtype=np.uint8)
    import cv2

    bar = cv2.resize(barcode, (bar.shape[1], bar.shape[0]), interpolation=cv2.INTER_NEAREST)
    y0 = (scene.shape[0] - bar.shape[0]) // 2
    x0 = (scene.shape[1] - bar.shape[1]) // 2
    scene[y0 : y0 + bar.shape[0], x0 : x0 + bar.shape[1]] = bar
    result = decode_student_barcode(scene)
    assert result["found"] is True
    assert result["student_id"] == "SE170999"


def test_blank_image_does_not_raise():
    image = np.zeros((120, 360, 3), dtype=np.uint8)
    result = decode_student_barcode(image)
    assert result["found"] is False
    assert result["student_id"] is None
