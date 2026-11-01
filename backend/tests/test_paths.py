"""Đường dẫn dev: QML + model + SQLite vẫn nằm trong repo."""
from pathlib import Path

import paths


def test_dev_layout_not_frozen():
    assert paths.frozen() is False
    root = paths.resource_root()
    assert (root / "fkyc" / "qml" / "main.qml").is_file()
    assert (root / "assets" / "login.png").is_file()
    assert paths.qml_dir() == root / "fkyc" / "qml"
    assert paths.models_dir() == root / "backend" / "models"
    assert paths.models_dir().joinpath("minifasnet_v2.onnx").is_file()
    assert paths.models_dir().joinpath("vietocr", "cnn.onnx").is_file()
    data = paths.data_dir()
    assert data == Path(paths.__file__).resolve().parent / "data"
    assert data.is_dir()
