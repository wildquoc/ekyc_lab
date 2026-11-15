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


def _write_accounts(accounts: List[Tuple[str, str]]) -> None:
    path = accounts_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "users": [{"username": username, "password": password} for username, password in accounts]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_account(original: str, username: str, password: str) -> str:
    """Thêm hoặc sửa một tài khoản. Trả về lỗi, hoặc chuỗi rỗng khi đã ghi."""
    username = (username or "").strip()
    password = (password or "").strip()
    original = (original or "").strip()
    if not username or not password:
        return "Fill in username and password."
    if any(ch.isspace() for ch in username):
        return "Username cannot contain spaces."
    if original.lower() == "pkq" and username.lower() != "pkq":
        return "The admin username pkq cannot be changed."
    rows = load_manual_accounts()
    for saved, _password in rows:
        if saved.lower() == username.lower() and saved.lower() != original.lower():
            return "That username already exists."
    updated: List[Tuple[str, str]] = []
    replaced = False
    for saved, saved_pass in rows:
        if original and saved.lower() == original.lower():
            updated.append((username, password))
            replaced = True
        else:
            updated.append((saved, saved_pass))
    if original and not replaced:
        return "That user was not found."
    if not original:
        updated.append((username, password))
    _write_accounts(updated)
    return ""


def delete_account(username: str) -> str:
    """Xóa một tài khoản. Không xóa pkq."""
    username = (username or "").strip()
    if not username:
        return "That user was not found."
    if username.lower() == "pkq":
        return "The admin user pkq cannot be deleted."
    rows = load_manual_accounts()
    kept = [(saved, password) for saved, password in rows if saved.lower() != username.lower()]
    if len(kept) == len(rows):
        return "That user was not found."
    _write_accounts(kept)
    return ""


def is_exception_user(username: str) -> bool:
    key = (username or "").strip().lower()
    if not key:
        return False
    return any(name.lower() == key for name in exception_usernames())
