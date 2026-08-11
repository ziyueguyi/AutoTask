# -*- coding: utf-8 -*-
"""
刷新淘宝 mtop 令牌 _m_h5_tk。

通过 queryUserTaoCoin（可不带有效 sign）触发下发新 token。
Cookie 必须走 headers['cookie']，不要用 cookies=get_dict()。

注意：刷新请求使用独立的 urllib3 requests（与原 tx_sign 一致），
不要走 curl_cffi session.get，避免带上 Base 的 Content-Type/代理合并头。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, Callable

import requests


def _sleep_after_request(tip: str = "") -> None:
    """请求间隔；缺失 delay 模块时静默跳过，避免影响令牌写入。"""
    try:
        name = "tx_request_delay"
        if name not in sys.modules:
            path = Path(__file__).resolve().parent / "request_delay.py"
            if not path.is_file():
                return
            spec = importlib.util.spec_from_file_location(name, str(path))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        sys.modules[name].sleep_after_request(tip)
    except Exception:
        pass


REFRESH_URL = (
    "https://h5api.m.taobao.com/h5/"
    "mtop.taobao.pc.growth.taocoin.queryusertaocoin/1.0/"
)
REFRESH_PARAMS = {
    "jsv": "2.5.1",
    "appKey": "12574478",
    "v": "1.0",
    "timeout": "5000",
    "dataType": "jsonp",
    "valueType": "original",
    "jsonpIncPrefix": "tbbe",
    "api": "mtop.taobao.pc.growth.taocoin.queryUserTaoCoin",
    "type": "originaljsonp",
    "callback": "mtopjsonptbbe1",
    "data": "{}",
    "bx-ua": "fast-load",
}


def session_cookie_dict(session: Any) -> dict[str, str]:
    jar: dict[str, str] = {}
    try:
        for cookie in session.cookies.jar:
            if cookie.name and cookie.value is not None and str(cookie.value) != "":
                jar[cookie.name] = str(cookie.value)
    except Exception:
        pass
    if jar:
        return jar
    try:
        get_dict = getattr(session.cookies, "get_dict", None)
        if callable(get_dict):
            for k, v in (get_dict() or {}).items():
                if v is not None and str(v) != "":
                    jar[str(k)] = str(v)
            if jar:
                return jar
    except Exception:
        pass
    try:
        for k, v in dict(session.cookies).items():
            if v is not None and str(v) != "":
                jar[str(k)] = str(v)
    except Exception:
        pass
    return jar


def apply_cookies(session: Any, cookies: dict[str, str]) -> None:
    """清空并写入 Cookie 到 session（多 domain）。"""
    try:
        session.cookies.clear()
    except Exception:
        pass
    for name, value in (cookies or {}).items():
        if value is None or str(value) == "":
            continue
        for domain in (".taobao.com", ".tmall.com", "h5api.m.taobao.com"):
            try:
                session.cookies.set(name, str(value), domain=domain)
            except Exception:
                try:
                    session.cookies.set(name, str(value))
                except Exception:
                    pass


def session_cookie_header(session: Any, cookies: dict[str, str] | None = None) -> str:
    jar = cookies if cookies is not None else session_cookie_dict(session)
    return "; ".join(
        f"{k}={v}" for k, v in jar.items() if v is not None and str(v) != ""
    )


def _cookies_from_set_cookie(response: Any) -> dict[str, str]:
    """从 Set-Cookie 头兜底解析（Partitioned/SameSite 时 response.cookies 常为空）。"""
    jar: dict[str, str] = {}
    headers = getattr(response, "headers", None)
    if headers is None:
        return jar

    raw_list: list[str] = []
    for getter in ("get_list", "getlist", "get_all"):
        if hasattr(headers, getter):
            try:
                raw_list = list(
                    getattr(headers, getter)("set-cookie")
                    or getattr(headers, getter)("Set-Cookie")
                    or []
                )
            except Exception:
                raw_list = []
            if raw_list:
                break
    if not raw_list:
        single = None
        try:
            single = headers.get("set-cookie") or headers.get("Set-Cookie")
        except Exception:
            single = None
        if single:
            # Expires 含逗号，不能简单按逗号拆
            parts = re.split(r",(?=\s*[^;=]+=)", str(single))
            raw_list = [p.strip() for p in parts if p.strip()]

    for item in raw_list:
        first = str(item).split(";", 1)[0].strip()
        if "=" not in first:
            continue
        name, value = first.split("=", 1)
        name, value = name.strip(), value.strip()
        if name:
            jar[name] = value
    return jar


def _cookies_from_jar(cookie_jar: Any) -> dict[str, str]:
    jar: dict[str, str] = {}
    if cookie_jar is None:
        return jar
    try:
        for c in cookie_jar:
            name = getattr(c, "name", None)
            value = getattr(c, "value", None)
            if name and value is not None and str(value) != "":
                jar[str(name)] = str(value)
    except Exception:
        pass
    if jar:
        return jar
    try:
        get = getattr(cookie_jar, "get", None)
        if callable(get):
            for key in ("_m_h5_tk", "_m_h5_tk_enc"):
                val = get(key)
                if val:
                    jar[key] = str(val)
    except Exception:
        pass
    return jar


def _extract_h5_tokens(response: Any) -> tuple[str | None, str | None]:
    """优先遍历 cookie jar，再兜底解析 Set-Cookie 头。"""
    parsed = _cookies_from_jar(getattr(response, "cookies", None))
    if "_m_h5_tk" not in parsed:
        parsed.update(_cookies_from_set_cookie(response))
    return parsed.get("_m_h5_tk"), parsed.get("_m_h5_tk_enc")


def query_user_taocoin(
    session: Any,
    cookies: dict[str, str] | None = None,
    *,
    on_ok: Callable[[str], None] | None = None,
    on_err: Callable[[str], None] | None = None,
    timeout: int = 20,
) -> bool:
    """
    拉取/刷新 _m_h5_tk，写回 session（若传入 cookies 也会更新该 dict）。

    :return: 是否拿到新的 _m_h5_tk
    """
    jar = dict(cookies) if cookies is not None else session_cookie_dict(session)
    if cookies is not None:
        apply_cookies(session, jar)

    cookie_header = session_cookie_header(session, jar)
    if not cookie_header.strip():
        if on_err:
            on_err("_m_h5_tk重置失败：Cookie 为空（session 未读到账号 Cookie）")
        return False

    headers = {
        "accept": "*/*",
        "accept-language": "zh,zh-CN;q=0.9",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": "https://jianghu.taobao.com/coin.html",
        "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "script",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-site": "same-site",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        ),
        "cookie": cookie_header,
    }
    try:
        response = requests.get(
            REFRESH_URL, params=REFRESH_PARAMS, headers=headers, timeout=timeout
        )
    except Exception as exc:
        if on_err:
            on_err(f"_m_h5_tk重置失败：请求异常 {exc}")
        return False

    # 先取 token，再休眠，避免 delay 模块异常导致“看起来没拿到 cookie”
    new_tk, new_enc = _extract_h5_tokens(response)
    _sleep_after_request("queryUserTaoCoin")

    if not new_tk:
        has_sc = bool(
            getattr(response, "headers", {}).get("set-cookie")
            or getattr(response, "headers", {}).get("Set-Cookie")
        )
        if on_err:
            on_err(
                f"_m_h5_tk重置失败（HTTP {getattr(response, 'status_code', '?')}，"
                f"Set-Cookie={'有' if has_sc else '无'}，Cookie字段数={len(jar)}）"
            )
        return False

    updated = {
        **session_cookie_dict(session),
        **jar,
        "_m_h5_tk": new_tk,
    }
    if new_enc:
        updated["_m_h5_tk_enc"] = new_enc
    apply_cookies(session, updated)
    if cookies is not None:
        cookies.clear()
        cookies.update(updated)
    if on_ok:
        on_ok("_m_h5_tk重置成功")
    return True


def ensure_m_h5_tk(
    session: Any,
    cookies: dict[str, str],
    *,
    on_ok: Callable[[str], None] | None = None,
    on_err: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """
    保证 cookies / session 中有 _m_h5_tk；没有则调用 query_user_taocoin 刷新。
    返回最新 cookies dict。
    """
    apply_cookies(session, cookies)
    token = str(cookies.get("_m_h5_tk") or "").split("_", 1)[0]
    if token:
        return cookies
    ok = query_user_taocoin(session, cookies, on_ok=on_ok, on_err=on_err)
    if not ok or not str(cookies.get("_m_h5_tk") or "").split("_", 1)[0]:
        raise RuntimeError("Cookie 缺少 _m_h5_tk，且自动获取失败")
    return cookies
