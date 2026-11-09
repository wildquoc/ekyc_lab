"""Đọc tài khoản đăng nhập thủ công từ file bảo mật."""
from __future__ import annotations

import json
from typing import List, Tuple

from paths import accounts_file, exceptions_file


def load_manual_accounts() -> List[Tuple[str, str]]:
    path = accounts_file()
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("users") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    accounts: List[Tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        username = str(row.get("username") or "").strip()
        password = str(row.get("password") or "")
        if username and password:
            accounts.append((username, password))
    return accounts


def exception_usernames() -> List[str]:
    path = exceptions_file()
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("users") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    names: List[str] = []
    for row in rows:
        name = str(row or "").strip()
        if name:
            names.append(name)
    return names


def is_exception_user(username: str) -> bool:
    key = (username or "").strip().lower()
    if not key:
        return False
    return any(name.lower() == key for name in exception_usernames())
