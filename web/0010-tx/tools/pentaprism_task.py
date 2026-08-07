# -*- coding: utf-8 -*-
"""
淘宝 pentaprism 场景任务工具（query / trigger）。

API:
  mtop.taobao.pentaprism.scene.query
  mtop.taobao.pentaprism.scene.trigger
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable

from curl_cffi import requests

APP_KEY = "12574478"
DEFAULT_TAO_COIN_SCENE_ID = "8676"
DEFAULT_TAO_COIN_ASAC = "2A24A178YUFG02XVGJNZFM"
DEFAULT_PAGE_URL = "https://huodong.taobao.com/wow/z/tbhome/pc-growth/tao-coin"
DEFAULT_REFERER = "https://huodong.taobao.com/"

PENDING_STATUSES = {"", "ACCEPTED", "INIT"}


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


def build_risk_ua(cookies: dict | None = None) -> str:
    """风控 ua（形如 140#...）。后期自行实现，当前返回空串。"""
    return ""


def _mtop_sign(cookies: dict, data: str) -> tuple[str, str]:
    token = str(cookies.get("_m_h5_tk", "")).split("_", 1)[0]
    if not token:
        raise RuntimeError("Cookie 缺少 _m_h5_tk")
    t = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{token}&{t}&{APP_KEY}&{data}".encode()).hexdigest()
    return t, sign


def _default_headers(referer: str = DEFAULT_REFERER) -> dict:
    return {
        "accept": "*/*",
        "accept-language": "zh,zh-CN;q=0.9",
        "referer": referer,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        ),
    }


def mtop_get(
    cookies: dict,
    api: str,
    data: str,
    *,
    session: requests.Session,
    extra_params: dict | None = None,
    referer: str = DEFAULT_REFERER,
    timeout: int = 20,
    proxies: dict | None = None,
) -> dict:
    if session is None:
        raise ValueError("必须传入 session，禁止单独 requests 请求")
    if proxies:
        session.proxies = proxies
    t, sign = _mtop_sign(cookies, data)
    params = {
        "jsv": "2.5.1",
        "appKey": APP_KEY,
        "t": t,
        "sign": sign,
        "api": api,
        "v": "1.0",
        "timeout": "5000",
        "dataType": "jsonp",
        "callback": "mtopjsonp1",
        "data": data,
    }
    if extra_params:
        params.update(extra_params)
    url = f"https://h5api.m.taobao.com/h5/{api}/1.0/"
    response = session.get(
        url,
        params=params,
        cookies=cookies,
        headers=_default_headers(referer),
        timeout=timeout,
    )
    return parse_jsonp(response.text)


def build_query_data(scene_id: str, asac: str | None = None) -> str:
    payload: dict[str, Any] = {"sceneId": str(scene_id)}
    if asac:
        payload["asac"] = asac
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def query_scene(
    cookies: dict,
    scene_id: str = DEFAULT_TAO_COIN_SCENE_ID,
    *,
    asac: str | None = DEFAULT_TAO_COIN_ASAC,
    page_url: str = DEFAULT_PAGE_URL,
    session: requests.Session,
    referer: str = DEFAULT_REFERER,
    timeout: int = 20,
    proxies: dict | None = None,
) -> dict:
    """查询场景任务列表，返回完整 mtop 响应。"""
    data = build_query_data(scene_id, asac)
    return mtop_get(
        cookies,
        "mtop.taobao.pentaprism.scene.query",
        data,
        session=session,
        referer=referer,
        timeout=timeout,
        proxies=proxies,
        extra_params={
            "type": "jsonp",
            "isSec": "1",
            "secType": "2",
            "pageUrl": page_url,
            "preventFallback": "true",
            "callback": "mtopjsonp12",
        },
    )


def resolve_task_params(item: dict) -> dict:
    params = dict(item.get("taskParams") or {})
    if params.get("deliveryId") and params.get("implId"):
        return params
    for sub in item.get("subList") or []:
        sub_params = sub.get("taskParams") or {}
        if sub_params.get("deliveryId") and sub_params.get("implId"):
            return dict(sub_params)
    return params


def task_title(item: dict) -> str:
    assets = item.get("assets") or {}
    if assets.get("title"):
        return str(assets["title"])
    center = ((item.get("theme") or {}).get("center") or {})
    if center.get("processTitle"):
        return str(center["processTitle"])
    for sub in item.get("subList") or []:
        title = task_title(sub)
        if title and not title.startswith("任务"):
            return title
    return f"任务{item.get('id', '?')}"


def task_status(item: dict) -> str:
    if str(item.get("complete")).lower() == "true":
        return "已完成"
    prog = item.get("progress") or {}
    status = prog.get("status") or item.get("status") or "未知"
    times = prog.get("times", "0")
    need = prog.get("needTimes", "1")
    mapping = {
        "ACCEPTED": "待完成",
        "COMPLETED": "已完成",
        "COMPLETE": "已完成",
        "AWARD": "待领取",
        "AWARDING": "待领奖",
    }
    if str(item.get("status") or "") == "AWARDING":
        return f"{mapping['AWARDING']}({times}/{need})"
    return f"{mapping.get(status, status)}({times}/{need})"


def task_coin(item: dict) -> str:
    rewards = item.get("rewards") or []
    if not rewards:
        for sub in item.get("subList") or []:
            rewards = sub.get("rewards") or []
            if rewards:
                break
    if not rewards:
        return "-"
    result = rewards[0].get("result") or {}
    return str(result.get("displayMinCount") or result.get("minCount") or "-")


def task_url(item: dict) -> str:
    assets = item.get("assets") or {}
    for key in ("action", "prepubAction"):
        if assets.get(key):
            return str(assets[key])
    center = ((item.get("theme") or {}).get("center") or {})
    process_desc = center.get("processDesc") or ""
    if process_desc.startswith("http"):
        return str(process_desc)
    if process_desc.startswith("{"):
        try:
            url = (json.loads(process_desc) or {}).get("url")
            if url:
                return str(url)
        except Exception:
            pass
    for sub in item.get("subList") or []:
        url = task_url(sub)
        if url and url != "-":
            return url
    return "-"


def is_jump_task(item: dict) -> bool:
    task_type = str(item.get("taskType") or "")
    if task_type in {"task_jump", "system_task_browse"}:
        return True
    assets = item.get("assets") or {}
    return bool(assets.get("action") or assets.get("prepubAction"))


def is_task_pending(item: dict) -> bool:
    if str(item.get("complete")).lower() == "true":
        return False
    status = str(item.get("status") or (item.get("progress") or {}).get("status") or "")
    if status in {"AWARDING", "COMPLETE", "COMPLETED", "DONE", "FINISH"}:
        return False
    prog = item.get("progress") or {}
    if str(prog.get("status") or "") in {"COMPLETE", "COMPLETED"}:
        return False
    return status in PENDING_STATUSES or str(prog.get("status") or "") in PENDING_STATUSES


def build_trigger_data(
    item: dict,
    *,
    cookies: dict | None = None,
    ua_builder: Callable[[dict | None], str] | None = None,
) -> str:
    params = resolve_task_params(item)
    delivery_id = str(params.get("deliveryId") or item.get("id") or "")
    impl_id = str(params.get("implId") or "")
    if not delivery_id or not impl_id:
        raise RuntimeError(f"任务缺少 taskParams：{task_title(item)}")
    payload = {
        "sceneId": str(params.get("sceneId") or DEFAULT_TAO_COIN_SCENE_ID),
        "deliveryId": delivery_id,
        "implId": impl_id,
        "asac": str(params.get("asac") or DEFAULT_TAO_COIN_ASAC),
    }
    builder = ua_builder or build_risk_ua
    ua = (builder(cookies) or "").strip()
    if ua:
        payload["ua"] = ua
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def trigger_scene(
    cookies: dict,
    item: dict,
    *,
    session: requests.Session,
    page_url: str = DEFAULT_PAGE_URL,
    referer: str = DEFAULT_REFERER,
    ua_builder: Callable[[dict | None], str] | None = None,
    timeout: int = 20,
    proxies: dict | None = None,
) -> dict:
    """触发任务完成（scene.trigger），返回完整 mtop 响应。"""
    data = build_trigger_data(item, cookies=cookies, ua_builder=ua_builder)
    return mtop_get(
        cookies,
        "mtop.taobao.pentaprism.scene.trigger",
        data,
        session=session,
        referer=referer,
        timeout=timeout,
        proxies=proxies,
        extra_params={
            "type": "jsonp",
            "isSec": "1",
            "secType": "2",
            "pageUrl": page_url,
            "preventFallback": "true",
            "callback": "mtopjsonp1",
        },
    )


def visit_task_url(
    cookies: dict,
    url: str,
    *,
    session: requests.Session,
    referer: str = DEFAULT_PAGE_URL,
    duration: int = 0,
    timeout: int = 20,
    proxies: dict | None = None,
) -> int:
    if not url or url == "-":
        raise RuntimeError("任务 URL 为空")
    if session is None:
        raise ValueError("必须传入 session，禁止单独 requests 请求")
    if proxies:
        session.proxies = proxies
    response = session.get(
        url,
        cookies=cookies,
        headers={
            **_default_headers(referer),
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        allow_redirects=True,
        timeout=timeout,
    )
    if duration > 0:
        time.sleep(duration)
    return response.status_code


def iter_pending_jump_tasks(data: dict) -> list[dict]:
    model = (data or {}).get("model") or []
    return [item for item in model if is_jump_task(item) and is_task_pending(item)]
