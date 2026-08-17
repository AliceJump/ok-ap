"""账号作用域配置存储：账号列表 + 按账号/任务覆盖的配置。

数据保存在 configs/account_scoped_overrides.json（运行时数据，不入库）。
模板提供最小实现：账号列表文本与 {账号: {任务类名: {配置}}} 覆盖字典。
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from ok.util.file import get_relative_path, read_json_file, write_json_file

_STORE_PATH = get_relative_path("configs", "account_scoped_overrides.json")
_LOCK = threading.Lock()

DEFAULT_DATA: Dict[str, Any] = {
    "account_list_text": "",
    "accounts": {},  # {account_key: {task_class: {config}}}
    "account_registry": {},  # {account_key: {username: str}}
}


def _load_raw() -> dict:
    data = read_json_file(_STORE_PATH)
    if not isinstance(data, dict):
        return dict(DEFAULT_DATA)
    merged = dict(DEFAULT_DATA)
    merged.update(data)
    return merged


def load_overrides(force: bool = False) -> dict:
    """读取完整覆盖数据（内存态）。"""
    return _load_raw()


def update_overrides(mutator) -> dict:
    """原子更新覆盖数据。mutator(latest) 返回新的完整数据。"""
    with _LOCK:
        data = _load_raw()
        data = mutator(data)
        write_json_file(_STORE_PATH, data)
        return data


def parse_account_list_text(text: str) -> list[Dict[str, str]]:
    """每行一个账号；兼容旧格式 `账号, 密码`（密码会被忽略且不存储）。"""
    entries = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(",")]
        username = parts[0].strip()
        if not username:
            continue
        entry = {"username": username}
        if len(parts) > 1 and parts[1]:
            entry["password"] = parts[1]
        entries.append(entry)
    return entries


def sync_account_list_text(text: str) -> dict:
    """保存账号列表并同步 account_registry（账号名是唯一 ID）。

    Returns:
        {"created_count": int, "reused_count": int, "invalid_count": int}
    """
    result = {"created_count": 0, "reused_count": 0, "invalid_count": 0}

    def apply(latest: dict) -> dict:
        latest["account_list_text"] = (text or "").strip()
        registry = latest.setdefault("account_registry", {})
        seen_keys = set()
        for entry in parse_account_list_text(text):
            username = entry["username"]
            existing_key = next(
                (key for key, meta in registry.items()
                 if isinstance(meta, dict) and meta.get("username") == username),
                None,
            )
            if existing_key is None:
                key = username
                registry[key] = {"username": username}
                result["created_count"] += 1
            else:
                key = existing_key
                registry[key]["username"] = username
                result["reused_count"] += 1
            seen_keys.add(key)
        # 清理不再存在的账号 registry 与覆盖
        for key in [k for k in registry if k not in seen_keys]:
            registry.pop(key, None)
        accounts = latest.setdefault("accounts", {})
        for key in [k for k in accounts if k not in seen_keys]:
            accounts.pop(key, None)
        return latest

    update_overrides(apply)
    return result


def get_account_map_content(account_key: str, account_name: str = "") -> str:
    """读取账号保存的官方地图同步 content（模板默认空实现）。"""
    return ""