# -*- coding: utf-8 -*-
"""
青龙面板多账号 Cookie / Token 加载（仅环境变量）。

环境变量多账号分隔（与夸克/JD 类似）：
  - && 连接多个账号
  - 或换行（青龙环境变量里一行一个账号）

单账号支持三种格式：
  1. JSON / Python 字典：{"COOKIE_LOGIN_USER":"xxx"} 或 {'COOKIE_LOGIN_USER':'xxx'}
  2. 键值串：COOKIE_LOGIN_USER=xxx; JSESSIONID=yyy
  3. 纯字符串（秘钥/Token）：直接填 xxx，解析为 {"token":"xxx"}
"""
import ast
import json
import os


def split_multi_account(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if "&&" in raw:
        return [p.strip() for p in raw.split("&&") if p.strip()]
    if "\n" in raw:
        return [p.strip() for p in raw.splitlines() if p.strip()]
    # Cookie 串里常有 utm 的 &，勿按单个 & 拆账号；多账号请用 && 或换行
    cookie_like = ";" in raw and "=" in raw and not raw.startswith("{")
    if "&" in raw and not cookie_like:
        return [p.strip() for p in raw.split("&") if p.strip()]
    return [raw]


def parse_object_item(item: str) -> dict:
    """解析 JSON 对象，兼容青龙里误填的 Python 单引号字典。"""
    try:
        data = json.loads(item)
    except json.JSONDecodeError:
        try:
            data = ast.literal_eval(item)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(
                "对象格式无效：请用标准 JSON 双引号，"
                '如 {"COOKIE_LOGIN_USER":"xxx"}，'
                "或直接填 Cookie 串 COOKIE_LOGIN_USER=xxx; ..."
            ) from exc
    if not isinstance(data, dict):
        raise ValueError("账号对象必须是字典/JSON 对象")
    # 统一成 str 键值，便于后续拼 Cookie
    return {str(k): ("" if v is None else str(v)) for k, v in data.items()}


def parse_cookie_item(item: str) -> dict:
    item = item.strip()
    if not item:
        raise ValueError("Cookie 为空")
    if item.startswith("{") or item.startswith("["):
        return parse_object_item(item)
    cookies = {}
    for part in item.split(";"):
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()
    if cookies:
        return cookies
    # 纯 Token / 秘钥：无 JSON、无 key=value
    return {"token": item}


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
