"""Ảnh camera mới nhất cho scheme image://camera/live."""
from __future__ import annotations

import threading

from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class CameraImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._lock = threading.Lock()
        self._image = QImage(16, 16, QImage.Format.Format_RGB888)
        self._image.fill(0)
        self._shot = QImage(16, 16, QImage.Format.Format_RGB888)
        self._shot.fill(0)

    def set_image(self, image: QImage) -> None:
        with self._lock:
            self._image = image

    def set_snapshot(self, image: QImage) -> None:
        with self._lock:
            self._shot = image

    def requestImage(self, image_id: str, size, requestedSize):  # noqa: N802
        key = (image_id or "").split("?")[0]
        with self._lock:
            image = self._shot if key.startswith("shot") else self._image
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image
