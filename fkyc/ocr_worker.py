"""Luồng OCR riêng: chỉ giữ frame mới nhất, không chặn camera / QML."""
from __future__ import annotations

import time

from PySide6.QtCore import QThread

from fkyc.pipeline import SessionEngine


class OcrWorker(QThread):
    def __init__(self, engine: SessionEngine) -> None:
        super().__init__()
        self._engine = engine
        self._running = True

    def stop(self) -> None:
        self._running = False
        self.wait(4000)

    def run(self) -> None:
        from id_card_ocr import engine as ocr

        while self._running and not ocr.ready and not ocr._error:
            ocr._load()
            time.sleep(0.04)
        while self._running:
            job = self._engine.take_ocr_job()
            if job is None:
                time.sleep(0.012)
                continue
            try:
                result = ocr.scan(job, known_fields=None)
            except Exception as exc:
                result = {
                    "ocr_ready": ocr.ready,
                    "complete": False,
                    "fields": {},
                    "guidance": f"OCR lỗi: {exc}",
                    "color": "red",
                    "ocr_ran": False,
                }
            self._engine.push_ocr_result(result)
