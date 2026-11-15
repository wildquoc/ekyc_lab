from __future__ import annotations

import sys

from fkyc.main import _bootstrap


def main() -> None:
    qml_dir = _bootstrap()
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType

    from fkyc.bridge import Bridge
    from fkyc.camera_worker import CameraWorker
    from fkyc.image_provider import CameraImageProvider

    app = QGuiApplication(sys.argv)
    app.setApplicationName("ADMIN")
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
    engine.rootContext().setContextProperty("assetRoot", _bootstrap.shell_assets.resolve().as_uri())
    shared = _bootstrap.shared_assets
    engine.rootContext().setContextProperty("logoSource", (shared / "Logo_FPT_UNIVERSITY_WHITE.png").resolve().as_uri())
    engine.rootContext().setContextProperty("loginIcon", (shared / "login.png").resolve().as_uri())
    engine.load(QUrl.fromLocalFile(str(qml_dir / "admin.qml")))
    if not engine.rootObjects():
        worker.shutdown()
        sys.exit(1)
    engine.rootObjects()[0].showMaximized()

    def _quit() -> None:
        worker.shutdown()

    app.aboutToQuit.connect(_quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
