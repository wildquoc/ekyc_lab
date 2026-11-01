"""VietOCR vgg_seq2seq chạy bằng onnxruntime trên CPU (CNN + GRU encoder + decoder từng bước)."""
from __future__ import annotations

import math
import os
from typing import Dict, Optional

import cv2
import numpy as np

_DIR = os.path.join(os.path.dirname(__file__), "models", "vietocr")
_GO, _EOS = 1, 2
_PAD_MIN_W = 32
_DEFAULT_MAX_W = 400


def onnx_files_present(root: str = _DIR) -> bool:
    return all(
        os.path.isfile(os.path.join(root, name))
        for name in ("cnn.onnx", "encoder.onnx", "decoder.onnx", "vocab.txt")
    )


def _session_options(intra: int):
    import onnxruntime as ort

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = max(1, intra)
    opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.enable_mem_pattern = True
    opts.enable_cpu_mem_arena = True
    return opts


def _load_vocab(path: str) -> Dict[int, str]:
    with open(path, encoding="utf-8") as handle:
        chars = handle.read()
        if chars.endswith("\n"):
            chars = chars[:-1]
        if chars.endswith("\r"):
            chars = chars[:-1]
    table = {0: "", 1: "", 2: "", 3: ""}
    for idx, ch in enumerate(chars):
        table[idx + 4] = ch
    return table


def preprocess_bgr(img_bgr: np.ndarray, max_width: int = _DEFAULT_MAX_W) -> np.ndarray:
    """RGB NCHW float32, cao 32px, rộng làm tròn 10 — khớp VietOCR."""
    if img_bgr is None or img_bgr.size == 0:
        raise ValueError("empty roi")
    if img_bgr.ndim == 2:
        img_bgr = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2BGR)
    height, width = img_bgr.shape[:2]
    if height < 4 or width < 4:
        raise ValueError("roi too small")
    new_w = int(math.ceil((32.0 * width / height) / 10.0) * 10)
    new_w = max(_PAD_MIN_W, min(int(max_width), new_w))
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (new_w, 32), interpolation=cv2.INTER_CUBIC)
    arr = np.ascontiguousarray(rgb.transpose(2, 0, 1), dtype=np.float32)
    arr *= np.float32(1.0 / 255.0)
    return arr[None, ...]


class VietOcrOnnx:
    def __init__(self, root: str = _DIR, intra_threads: Optional[int] = None) -> None:
        import onnxruntime as ort

        if not onnx_files_present(root):
            raise FileNotFoundError(f"Thiếu file ONNX VietOCR trong {root}")
        cpu = os.cpu_count() or 2
        intra = intra_threads if intra_threads is not None else min(4, max(2, cpu // 2))
        opts = _session_options(intra)
        providers = ["CPUExecutionProvider"]
        self.cnn = ort.InferenceSession(os.path.join(root, "cnn.onnx"), opts, providers=providers)
        self.encoder = ort.InferenceSession(os.path.join(root, "encoder.onnx"), opts, providers=providers)
        self.decoder = ort.InferenceSession(os.path.join(root, "decoder.onnx"), opts, providers=providers)
        self.i2c = _load_vocab(os.path.join(root, "vocab.txt"))
        self.intra_threads = intra

    def warmup(self) -> None:
        dummy = np.zeros((40, 160, 3), dtype=np.uint8)
        dummy[:] = 240
        self.predict(dummy, max_len=4, max_width=160)

    def predict(self, img_bgr: np.ndarray, max_len: int = 32, max_width: int = _DEFAULT_MAX_W) -> str:
        try:
            image = preprocess_bgr(img_bgr, max_width=max_width)
        except ValueError:
            return ""
        src = self.cnn.run(None, {"image": image})[0]
        encoder_outputs, hidden = self.encoder.run(None, {"src": src})
        token = np.array([_GO], dtype=np.int64)
        chars: list[str] = []
        for _ in range(max(1, int(max_len))):
            logits, hidden = self.decoder.run(
                None,
                {
                    "token": token,
                    "hidden": hidden,
                    "encoder_outputs": encoder_outputs,
                },
            )
            idx = int(logits[0].argmax())
            if idx == _EOS or idx < 4:
                break
            chars.append(self.i2c.get(idx, ""))
            token = np.array([idx], dtype=np.int64)
        return "".join(chars).strip()
