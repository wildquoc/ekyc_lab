"""Webcam, nhận diện khuôn mặt và OCR chạy trên các luồng tách biệt.

Luồng đọc camera chỉ lật gương và đẩy ảnh lên màn hình. Khuôn mặt / mã vạch
chạy trên InferenceLoop. OCR CCCD chạy trên OcrWorker (QThread), không giật QML.
"""
from __future__ import annotations

import json
import queue
import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from fkyc.image_provider import CameraImageProvider
from fkyc.pipeline import SessionEngine


def _kick_ocr() -> None:
    try:
        from id_card_ocr import engine as ocr_engine

        ocr_engine._load()
    except Exception as exc:
        try:
            from id_card_ocr import engine as ocr_engine

            ocr_engine._error = f"Không thể nạp VietOCR: {exc}"
        except Exception:
            pass


class _InferenceLoop(QThread):
    def __init__(self, owner: "CameraWorker") -> None:
        super().__init__()
        self._owner = owner

    def run(self) -> None:
        owner = self._owner
        while owner._running:
            owner._drain_commands()
            if not owner.engine.camera_on:
                owner.camera_enabled.clear()
                time.sleep(0.03)
                continue
            owner.camera_enabled.set()
            frame, fps = owner._take_frame()
            if frame is None:
                continue
            patch = owner.engine.on_frame(frame, fps)
            shot = owner.engine.take_snapshot()
            if shot is not None:
                owner._publish_snapshot(shot)
            owner._emit(patch)
            if not owner.engine.camera_on:
                owner.camera_enabled.clear()


class CameraWorker(QThread):
    uiEvent = Signal(str)
    frameReady = Signal()

    def __init__(self, provider: CameraImageProvider) -> None:
        super().__init__()
        self._provider = provider
        self.engine = SessionEngine()
        self._commands: queue.Queue[str] = queue.Queue()
        self._slot_lock = threading.Lock()
        self._slot: tuple | None = None
        self._running = True
        self.camera_enabled = threading.Event()
        self._engine_lock = threading.Lock()
        self._infer = _InferenceLoop(self)
        self._ocr = None
        self._tap = threading.Event()

    def submit(self, command: str) -> None:
        self._commands.put(command)

    def request_focus(self) -> None:
        self._tap.set()

    def start(self, priority: QThread.Priority = QThread.Priority.InheritPriority) -> None:
        from fkyc.ocr_worker import OcrWorker

        threading.Thread(target=_kick_ocr, name="vietocr-warmup", daemon=True).start()
        threading.Thread(target=self.engine._load, name="fkyc-warmup", daemon=True).start()
        self._ocr = OcrWorker(self.engine)
        self._ocr.start()
        self._infer.start()
        super().start(priority)

    def shutdown(self) -> None:
        self._running = False
        self.camera_enabled.set()
        if self._ocr is not None:
            self._ocr.stop()
        self._infer.wait(4000)
        self.wait(3000)

    def run(self) -> None:
        cap = None
        last = time.perf_counter()
        last_pub = 0.0
        fps = 0.0
        while self._running:
            if not self.camera_enabled.is_set():
                if cap is not None:
                    cap.release()
                    cap = None
                time.sleep(0.03)
                continue
            if cap is None:
                cap = self._open_camera()
                if cap is None:
                    time.sleep(0.2)
                    continue
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue
            frame = cv2.flip(frame, 1)
            if self._tap.is_set():
                self._tap.clear()
                self._refocus(cap)
            now = time.perf_counter()
            dt = now - last
            last = now
            if dt > 1e-4:
                inst = 1.0 / dt
                fps = inst if fps == 0 else (0.85 * fps + 0.15 * inst)
            if now - last_pub >= 1.0 / 24.0:
                last_pub = now
                self._publish(frame)
            self._offer(frame, fps)
        if cap is not None:
            cap.release()

    def _offer(self, frame: np.ndarray, fps: float) -> None:
        with self._slot_lock:
            current = self._slot
            if current is not None and current[0].shape == frame.shape:
                np.copyto(current[0], frame)
                self._slot = (current[0], fps)
            else:
                self._slot = (frame.copy(), fps)

    def _take_frame(self):
        with self._slot_lock:
            item = self._slot
            self._slot = None
        if item is None:
            time.sleep(0.02)
            return None, 0.0
        return item

    def _drain_commands(self) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            with self._engine_lock:
                patch = self.engine.submit(command)
            if self.engine.camera_on:
                self.camera_enabled.set()
            else:
                self.camera_enabled.clear()
            self._emit(patch)
            self._clear_frames()

    def _clear_frames(self) -> None:
        with self._slot_lock:
            self._slot = None

    def _open_camera(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.camera_enabled.clear()
            with self._engine_lock:
                self.engine.camera_on = False
                patch = self.engine._mark(
                    errorText="Không mở được camera. Hãy kiểm tra camera.",
                    cameraActive=False,
                    screen="landing",
                )
            self._emit(patch)
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        try:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        except Exception:
            pass
        # Webcam DirectShow hay kẹt exposure thủ công (màn hình đen) sau lần chỉnh trước.
        for auto_exp in (0.75, 3.0, 1.0):
            try:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, auto_exp)
            except Exception:
                pass
        for _ in range(6):
            cap.read()
        return cap

    def _refocus(self, cap) -> None:
        try:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        except Exception:
            pass

    def _publish_snapshot(self, frame: np.ndarray) -> None:
        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        self._provider.set_snapshot(image)

    def _publish(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        if width > 960:
            scale = 960.0 / float(width)
            frame = cv2.resize(
                frame,
                (960, max(1, int(round(height * scale)))),
                interpolation=cv2.INTER_AREA,
            )
        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        height, width, _ = rgb.shape
        image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        self._provider.set_image(image)
        self.frameReady.emit()

    def _emit(self, patch: dict) -> None:
        if patch:
            self.uiEvent.emit(json.dumps(patch, ensure_ascii=False))
