from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap() -> Path:
    root = Path(__file__).resolve().parents[1]
    backend = root / "backend"
    qml = root / "fkyc" / "qml"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    venv_site = root / ".venv" / "Lib" / "site-packages"
    if venv_site.is_dir() and str(venv_site) not in sys.path:
        sys.path.append(str(venv_site))
    os.chdir(root)
    return qml


def main() -> None:
    qml_dir = _bootstrap()
    # Chỉ nạp torch khi chưa có ONNX — tránh OpenMP deadlock với Qt.
    onnx_cnn = Path(__file__).resolve().parents[1] / "backend" / "models" / "vietocr" / "cnn.onnx"
    if not onnx_cnn.is_file():
        try:
            import torch

            torch.set_num_threads(1)
        except Exception:
            pass
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType

    from fkyc.bridge import Bridge
    from fkyc.camera_worker import CameraWorker
    from fkyc.image_provider import CameraImageProvider

    app = QGuiApplication(sys.argv)
    app.setApplicationName("FKYC")
    app.setOrganizationName("FPT")

    qmlRegisterSingletonType(
        QUrl.fromLocalFile(str(qml_dir / "Theme.qml")),
        "Fkyc",
        1,
        0,
        "Theme",
    )

    provider = CameraImageProvider()
    worker = CameraWorker(provider)
    bridge = Bridge(worker)
    worker.start()

    engine = QQmlApplicationEngine()
    engine.addImageProvider("camera", provider)
    engine.rootContext().setContextProperty("bridge", bridge)
    asset_root = (qml_dir.parent / "assets").resolve().as_uri()
    engine.rootContext().setContextProperty("assetRoot", asset_root)
    shared = qml_dir.parents[1] / "assets"
    engine.rootContext().setContextProperty("logoSource", (shared / "Logo_FPT_UNIVERSITY_WHITE.png").resolve().as_uri())
    engine.rootContext().setContextProperty("loginIcon", (shared / "login.png").resolve().as_uri())
    engine.load(QUrl.fromLocalFile(str(qml_dir / "main.qml")))
    if not engine.rootObjects():
        worker.shutdown()
        sys.exit(1)
    engine.rootObjects()[0].showMaximized()

    def _quit() -> None:
        worker.shutdown()

    app.aboutToQuit.connect(_quit)
    sys.exit(app.exec())
