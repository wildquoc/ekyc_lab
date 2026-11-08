# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir: python -m PyInstaller --noconfirm --clean fkyc.spec"""
from __future__ import annotations

import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(SPECPATH)

datas: list = []
binaries: list = []
hiddenimports: list = []

for pkg in ("PySide6", "mediapipe", "onnxruntime", "cv2"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

try:
    d, b, h = collect_all("zxingcpp")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    hiddenimports.append("zxingcpp")

datas += [
    (os.path.join(ROOT, "backend", "security", "accounts.json"), os.path.join("backend", "security")),
    (os.path.join(ROOT, "fkyc", "qml"), os.path.join("fkyc", "qml")),
    (os.path.join(ROOT, "fkyc", "assets"), os.path.join("fkyc", "assets")),
    (os.path.join(ROOT, "assets"), "assets"),
]

models = os.path.join(ROOT, "backend", "models")
datas += [
    (os.path.join(models, "minifasnet_v2.onnx"), os.path.join("backend", "models")),
    (os.path.join(models, "w600k_r50.onnx"), os.path.join("backend", "models")),
]
for name in ("cnn.onnx", "encoder.onnx", "decoder.onnx", "vocab.txt"):
    datas.append(
        (
            os.path.join(models, "vietocr", name),
            os.path.join("backend", "models", "vietocr"),
        )
    )

hiddenimports += [
    "fkyc",
    "fkyc.main",
    "fkyc.bridge",
    "fkyc.camera_worker",
    "fkyc.pipeline",
    "fkyc.ocr_worker",
    "fkyc.image_provider",
    "fkyc.hud_en",
    "config",
    "paths",
    "state",
    "database",
    "id_card_ocr",
    "student_card",
    "face_analyzer",
    "exam_monitor",
    "enrollment",
    "camera_quality",
    "color_challenge",
    "optical_analyzer",
    "feature_extractor",
    "anti_spoofing",
    "head_pose",
    "vietocr_onnx",
    "manual_accounts",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtQuickControls2",
]

a = Analysis(
    [os.path.join(ROOT, "fkyc", "__main__.py")],
    pathex=[ROOT, os.path.join(ROOT, "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(ROOT, "hooks", "pyi_rth_mediapipe.py")],
    excludes=[
        "torch",
        "torchvision",
        "torchaudio",
        "tensorflow",
        "matplotlib",
        "IPython",
        "tkinter",
        "vietocr",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FKYC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FKYC",
)
