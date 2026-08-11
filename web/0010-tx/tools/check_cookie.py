# -*- coding: utf-8 -*-
"""
通过 mtop.user.getUserSimple 检测淘宝 Cookie 是否有效。

有效条件：ret 为 SUCCESS，且 data.nick 或 data.userNumId 非空。
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from urllib.parse import unquote

import requests

APP_KEY = "12574478"
API = "mtop.user.getUserSimple"
URL = f"https://h5api.m.taobao.com/h5/{API.lower()}/1.0/"
DATA = "{}"


def cookies_header(cookies: dict) -> str:
    return "; ".join(
        f"{k}={v}" for k, v in (cookies or {}).items() if v is not None and str(v) != ""
    )


def account_label(cookies: dict, fallback: str = "") -> str:
    for key in ("tracknick", "lgc", "_nk_", "dnk", "unb"):
        val = str((cookies or {}).get(key) or "").strip()
        if val:
            return unquote(val)
    return fallback or "未知账号"


def account_id(cookies: dict) -> str:
    for key in ("unb", "tracknick", "lgc", "_nk_", "dnk"):
        val = str((cookies or {}).get(key) or "").strip()
        if val:
            return unquote(val)
    return ""


def parse_json(text: str) -> dict:
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


def mtop_sign(cookies: dict, data: str = DATA) -> tuple[str, str]:
    token = str((cookies or {}).get("_m_h5_tk", "")).split("_", 1)[0]
    if not token:
        raise RuntimeError("Cookie 缺少 _m_h5_tk")
    t = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{token}&{t}&{APP_KEY}&{data}".encode()).hexdigest()
    return t, sign


def refresh_m_h5_tk(cookies: dict, timeout: int = 20) -> bool:
    """无 token 或令牌过期时，用 queryUserTaoCoin 拉取新 _m_h5_tk。"""
    url = (
        "https://h5api.m.taobao.com/h5/"
        "mtop.taobao.pc.growth.taocoin.queryusertaocoin/1.0/"
    )
    params = {
        "jsv": "2.5.1",
        "appKey": APP_KEY,
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
    headers = {
        "accept": "*/*",
        "referer": "https://jianghu.taobao.com/coin.html",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        ),
        "cookie": cookies_header(cookies),
    }
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    new_tk = response.cookies.get("_m_h5_tk")
    new_enc = response.cookies.get("_m_h5_tk_enc")
    if not new_tk:
        return False
    cookies["_m_h5_tk"] = new_tk
    if new_enc:
        cookies["_m_h5_tk_enc"] = new_enc
    return True


def get_user_simple(
    cookies: dict,
    *,
    timeout: int = 20,
    auto_refresh_token: bool = True,
) -> dict[str, Any]:
    """
    调用 getUserSimple。

    :return: {
        ok, nick, user_num_id, message, raw
    }
    """
    jar = dict(cookies or {})
    if auto_refresh_token and not str(jar.get("_m_h5_tk") or "").split("_", 1)[0]:
        refresh_m_h5_tk(jar, timeout=timeout)

    def _request() -> dict:
        t, sign = mtop_sign(jar, DATA)
        params = {
            "jsv": "2.5.1",
            "appKey": APP_KEY,
            "t": t,
            "sign": sign,
            "jsonpIncPrefix": "tbnavnew",
            "api": API,
            "v": "1.0",
            "dataType": "json",
            "type": "originaljson",
            "data": DATA,
        }
        headers = {
            "accept": "application/json",
            "accept-language": "zh,zh-CN;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://huodong.taobao.com",
            "pragma": "no-cache",
            "referer": "https://huodong.taobao.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
            "cookie": cookies_header(jar),
        }
        response = requests.get(URL, params=params, headers=headers, timeout=timeout)
        return parse_json(response.text)

    try:
        payload = _request()
    except Exception as exc:
        return {
            "ok": False,
            "nick": "",
            "user_num_id": None,
            "message": f"请求异常：{exc}",
            "raw": {},
            "cookies": jar,
        }

    text = ret_msg(payload)
    if auto_refresh_token and ("令牌过期" in text or "TOKEN" in text.upper()):
        if refresh_m_h5_tk(jar, timeout=timeout):
            try:
                payload = _request()
                text = ret_msg(payload)
            except Exception as exc:
                return {
                    "ok": False,
                    "nick": "",
                    "user_num_id": None,
                    "message": f"令牌刷新后仍失败：{exc}",
                    "raw": {},
                    "cookies": jar,
                }

    data = (payload or {}).get("data") or {}
    nick = str(data.get("nick") or data.get("displayNick") or "").strip()
    user_num_id = data.get("userNumId")
    if user_num_id is not None and str(user_num_id).strip() == "":
        user_num_id = None

    ok = bool(ret_ok(payload) and (nick or user_num_id is not None))
    if ok:
        message = f"有效 nick={nick or '-'} userNumId={user_num_id if user_num_id is not None else '-'}"
    elif not ret_ok(payload):
        message = text
    else:
        message = "SUCCESS 但 nick / userNumId 均为空"

    return {
        "ok": ok,
        "nick": nick,
        "user_num_id": user_num_id,
        "message": message,
        "raw": payload,
        "cookies": jar,
    }
