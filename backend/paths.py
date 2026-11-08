"""Đường dẫn tài nguyên đóng gói và thư mục dữ liệu ghi được."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Thư mục đọc được: repo (dev) hoặc _MEIPASS (PyInstaller)."""
    if frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


def models_dir() -> Path:
    return resource_root() / "backend" / "models"


def qml_dir() -> Path:
    return resource_root() / "fkyc" / "qml"


def shell_assets_dir() -> Path:
    return resource_root() / "fkyc" / "assets"


def shared_assets_dir() -> Path:
    return resource_root() / "assets"


def accounts_file() -> Path:
    """File tài khoản đăng nhập thủ công. Bản đóng gói ưu tiên file cạnh exe."""
    if frozen():
        beside = Path(sys.executable).resolve().parent / "security" / "accounts.json"
        if beside.is_file():
            return beside
    return resource_root() / "backend" / "security" / "accounts.json"


def data_dir() -> Path:
    """SQLite + chân dung: cạnh source khi dev, %LOCALAPPDATA%\\FKYC khi đóng gói."""
    if frozen():
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        root = base / "FKYC"
    else:
        root = Path(__file__).resolve().parent / "data"
    root.mkdir(parents=True, exist_ok=True)
    (root / "portraits").mkdir(parents=True, exist_ok=True)
    return root


def log_dir() -> Path:
    if frozen():
        root = data_dir() / "logs"
    else:
        root = Path(__file__).resolve().parent / "logs"
    root.mkdir(parents=True, exist_ok=True)
    return root
