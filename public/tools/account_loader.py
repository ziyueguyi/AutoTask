# -*- coding: utf-8 -*-
"""
青龙面板多账号 Cookie 加载（仅环境变量）。

环境变量多账号分隔（与夸克/JD 类似）：
  - & 连接多个账号
  - 或换行（青龙环境变量里一行一个账号）

单账号支持两种格式：
  1. JSON：{"BDUSS":"xxx","STOKEN":"yyy"}
  2. 键值串：BDUSS=xxx;STOKEN=yyy
"""
import json
import os


def split_multi_account(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if "&" in raw:
        return [p.strip() for p in raw.split("&") if p.strip()]
    if "\n" in raw:
        return [p.strip() for p in raw.splitlines() if p.strip()]
    return [raw]


def parse_cookie_item(item: str) -> dict:
    item = item.strip()
    if not item:
        raise ValueError("Cookie 为空")
    if item.startswith("{"):
        data = json.loads(item)
        if not isinstance(data, dict):
            raise ValueError("JSON Cookie 必须是对象")
        return data
    cookies = {}
    for part in item.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()
    if not cookies:
        raise ValueError(f"无法解析 Cookie: {item[:120]}")
    return cookies


def load_accounts(env_name: str) -> list[tuple[str, dict]]:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return []
    accounts = []
    for index, item in enumerate(split_multi_account(raw), 1):
        try:
            accounts.append((f"环境变量账户{index}", parse_cookie_item(item)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"{env_name} 第{index}个账号解析失败: {exc}") from exc
    return accounts
