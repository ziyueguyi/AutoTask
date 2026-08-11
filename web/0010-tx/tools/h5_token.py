# -*- coding: utf-8 -*-
"""
刷新淘宝 mtop 令牌 _m_h5_tk。

通过 queryUserTaoCoin（可不带有效 sign）触发下发新 token。
Cookie 必须走 headers['cookie']，不要用 cookies=get_dict()。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

import requests


def _sleep_after_request(tip: str = "") -> None:
    name = "tx_request_delay"
    if name not in sys.modules:
        path = Path(__file__).resolve().parent / "request_delay.py"
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    sys.modules[name].sleep_after_request(tip)

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
            jar[cookie.name] = cookie.value
    except Exception:
        try:
            jar.update({k: str(v) for k, v in dict(session.cookies).items()})
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
        "cookie": session_cookie_header(session, jar),
    }
    response = requests.get(
        REFRESH_URL, params=REFRESH_PARAMS, headers=headers, timeout=timeout
    )
    _sleep_after_request("queryUserTaoCoin")
    new_tk = response.cookies.get("_m_h5_tk")
    new_enc = response.cookies.get("_m_h5_tk_enc")
    if not new_tk:
        if on_err:
            on_err("_m_h5_tk重置失败")
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
