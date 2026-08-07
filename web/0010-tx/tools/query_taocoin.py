# -*- coding: utf-8 -*-
"""
淘金币余额查询工具。

API: mtop.taobao.pc.growth.taocoin.queryUserTaoCoin
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from curl_cffi import requests

APP_KEY = "12574478"
API = "mtop.taobao.pc.growth.taocoin.queryUserTaoCoin"
DATA = "{}"


def parse_jsonp(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("mtopjsonp") and "(" in text:
        text = text[text.find("(") + 1: text.rfind(")")]
    return json.loads(text)


def ret_ok(payload: dict) -> bool:
    ret = (payload or {}).get("ret") or []
    return bool(ret) and str(ret[0]).startswith("SUCCESS")


def ret_msg(payload: dict) -> str:
    ret = (payload or {}).get("ret") or []
    return str(ret[0]) if ret else "未知错误"


def parse_coin_amount(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None


def extract_coin_info(payload: dict) -> tuple[int | None, str]:
    """从 queryUserTaoCoin 响应取出 (coin_amount, coin_saving)。"""
    outer = (payload or {}).get("data") or {}
    inner = outer.get("data") if isinstance(outer.get("data"), dict) else outer
    amount = parse_coin_amount((inner or {}).get("coinAmount"))
    saving = (inner or {}).get("coinSaving", "-")
    return amount, str(saving)


def _mtop_sign(cookies: dict, data: str) -> tuple[str, str]:
    token = str(cookies.get("_m_h5_tk", "")).split("_", 1)[0]
    if not token:
        raise RuntimeError("Cookie 缺少 _m_h5_tk")
    t = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{token}&{t}&{APP_KEY}&{data}".encode()).hexdigest()
    return t, sign


def query_user_taocoin(
    cookies: dict,
    session: requests.Session,
    *,
    timeout: int = 20,
    proxies: dict | None = None,
) -> dict:
    """
    查询淘金币余额。

    :param cookies: 淘宝 Cookie 字典（需含 _m_h5_tk）
    :param session: 必须传入已有 Session，不单独发请求
    :return: {
        "ok": bool,
        "coin_amount": int | None,
        "coin_saving": str,
        "message": str,
        "raw": dict,
    }
    """
    if session is None:
        raise ValueError("必须传入 session，禁止单独 requests 请求")
    if proxies:
        session.proxies = proxies
    t, sign = _mtop_sign(cookies, DATA)
    params = {
        "jsv": "2.5.1",
        "appKey": APP_KEY,
        "t": t,
        "sign": sign,
        "api": API,
        "v": "1.0",
        "timeout": "5000",
        "dataType": "jsonp",
        "valueType": "original",
        "jsonpIncPrefix": "tbbe",
        "type": "originaljsonp",
        "callback": "mtopjsonptbbe1",
        "data": DATA,
    }
    url = f"https://h5api.m.taobao.com/h5/{API}/1.0/"
    response = session.get(
        url,
        params=params,
        cookies=cookies,
        headers={
            "accept": "*/*",
            "referer": "https://jianghu.taobao.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        },
        timeout=timeout,
    )
    raw = parse_jsonp(response.text)
    ok = ret_ok(raw)
    amount, saving = extract_coin_info(raw) if ok else (None, "-")
    return {
        "ok": ok,
        "coin_amount": amount,
        "coin_saving": saving,
        "message": ret_msg(raw),
        "raw": raw,
    }
