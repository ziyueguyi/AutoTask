# -*- coding: utf-8 -*-
"""
淘宝 pentaprism 场景任务工具（query / trigger / award / clickGoodsAd）。

API:
  mtop.taobao.pentaprism.scene.query
  mtop.taobao.pentaprism.scene.trigger
  mtop.taobao.pentaprism.scene.award
  mtop.taobao.pc.growth.clickGoodsAd   # 逛/点击心仪商品计次
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from curl_cffi import requests

APP_KEY = "12574478"
DEFAULT_TAO_COIN_SCENE_ID = "8676"
DEFAULT_TAO_COIN_ASAC = "2A24A178YUFG02XVGJNZFM"
DEFAULT_JIANGHU_SCENE_ID = "8244"
DEFAULT_JIANGHU_ASAC = "2A24904DS0EK51UNN4AEG5"
DEFAULT_CLICK_GOODS_ASAC = "2A24904DS0EK51UNN4AEG5"
DEFAULT_PAGE_URL = "https://huodong.taobao.com/wow/z/tbhome/pc-growth/tao-coin"
DEFAULT_JIANGHU_PAGE_URL = "https://jianghu.taobao.com/coin.html"
DEFAULT_PRODUCT_TASK_URL = (
    "https://huodong.taobao.com/wow/z/tbhome/pc-growth/product-task"
)
PRODUCT_TASK_PATH = "product-task"
DEFAULT_REFERER = "https://huodong.taobao.com/"
DEFAULT_JIANGHU_REFERER = "https://jianghu.taobao.com/"

PENDING_STATUSES = {"", "ACCEPTED", "INIT"}
CLAIMABLE_STATUSES = {"AWARDING", "AWARD"}


def _sleep_after_request(tip: str = "") -> float:
    """每个请求后随机休眠 1～5 秒（与 tools/request_delay.py 一致）。"""
    name = "tx_request_delay"
    if name not in sys.modules:
        path = Path(__file__).resolve().parent / "request_delay.py"
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name].sleep_after_request(tip)


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
    payload = parse_jsonp(response.text)
    _sleep_after_request(api)
    return payload


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
    assets = item.get("assets") or {}
    btn = str(assets.get("acceptBtn") or "")
    prog = item.get("progress") or {}
    status = str(item.get("status") or prog.get("status") or "未知")
    times = prog.get("times", "0")
    need = prog.get("needTimes", "1")
    mapping = {
        "ACCEPTED": "待完成",
        "COMPLETED": "已完成",
        "COMPLETE": "已完成",
        "AWARD": "待领取",
        "AWARDING": "待领奖",
    }
    if status in {"AWARDING", "AWARD"} or "领" in btn:
        return f"待领取({times}/{need})"
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


def _process_desc(item: dict) -> dict:
    center = ((item.get("theme") or {}).get("center") or {})
    raw = center.get("processDesc") or ""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.startswith("{"):
        try:
            return json.loads(raw) or {}
        except Exception:
            return {}
    return {}


def is_click_goods_task(item: dict) -> bool:
    """逛 N 个商品 / 点击心仪商品：走 clickGoodsAd，不是 scene.trigger。"""
    desc = _process_desc(item)
    if str(desc.get("type") or "").lower() == "click":
        return True
    url = task_url(item)
    if PRODUCT_TASK_PATH in url:
        return True
    title = task_title(item)
    if "商品" in title and any(key in title for key in ("逛", "心仪", "点击")):
        return True
    return False


def is_jump_task(item: dict) -> bool:
    if is_click_goods_task(item):
        return False
    task_type = str(item.get("taskType") or "")
    if task_type in {"task_jump", "system_task_browse", "system_task_customize"}:
        return True
    assets = item.get("assets") or {}
    return bool(assets.get("action") or assets.get("prepubAction"))


def click_goods_need_times(item: dict) -> int:
    try:
        return max(int(item.get("awardThreshold") or 0), 1)
    except Exception:
        return 3


def click_goods_done_times(item: dict) -> int:
    proceeds = item.get("proceeds") or []
    if proceeds:
        return len(proceeds)
    prog = item.get("progress") or {}
    try:
        return max(int(prog.get("times") or 0), 0)
    except Exception:
        return 0


def click_goods_remain_times(item: dict) -> int:
    return max(click_goods_need_times(item) - click_goods_done_times(item), 0)


def is_task_pending(item: dict) -> bool:
    if str(item.get("complete")).lower() == "true":
        return False
    status = str(item.get("status") or (item.get("progress") or {}).get("status") or "")
    if status in {"AWARDING", "AWARD", "COMPLETE", "COMPLETED", "DONE", "FINISH"}:
        return False
    prog = item.get("progress") or {}
    if str(prog.get("status") or "") in {"COMPLETE", "COMPLETED"}:
        return False
    return status in PENDING_STATUSES or str(prog.get("status") or "") in PENDING_STATUSES


def is_task_claimable(item: dict) -> bool:
    """任务已完成、待领取奖励。"""
    if str(item.get("complete")).lower() == "true":
        return False
    status = str(item.get("status") or "")
    if status in CLAIMABLE_STATUSES:
        return True
    prog = item.get("progress") or {}
    if str(prog.get("status") or "") in CLAIMABLE_STATUSES:
        return True
    # 部分任务 status=AWARDING 但按钮仍显示「去完成」；progress 已 COMPLETE 也可领
    if status not in {"COMPLETE", "COMPLETED"} and str(prog.get("status") or "") in {
        "COMPLETE",
        "COMPLETED",
    }:
        return True
    assets = item.get("assets") or {}
    btn = str(assets.get("acceptBtn") or "")
    if "领" in btn:
        return True
    return False


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


def build_award_data(
        item: dict,
        *,
        cookies: dict | None = None,
        ua_builder: Callable[[dict | None], str] | None = None,
) -> str:
    """构造 scene.award 请求 data（字段来自 taskParams）。"""
    params = resolve_task_params(item)
    delivery_id = str(params.get("deliveryId") or item.get("id") or "")
    impl_id = str(params.get("implId") or "")
    if not delivery_id or not impl_id:
        raise RuntimeError(f"任务缺少 taskParams：{task_title(item)}")
    payload: dict[str, Any] = {
        "activityId": str(params.get("activityId") or ""),
        "asac": str(params.get("asac") or DEFAULT_TAO_COIN_ASAC),
        "awardIndex": str(params.get("awardIndex") or "1"),
        "deliveryId": delivery_id,
        "fromToken": str(params.get("fromToken") or ""),
        "implId": impl_id,
        "samplingRate": str(params.get("samplingRate") or "0"),
        "sceneId": str(params.get("sceneId") or DEFAULT_TAO_COIN_SCENE_ID),
    }
    if not payload["activityId"]:
        raise RuntimeError(f"任务缺少 activityId：{task_title(item)}")
    if not payload["fromToken"]:
        raise RuntimeError(f"任务缺少 fromToken：{task_title(item)}")
    builder = ua_builder or build_risk_ua
    ua = (builder(cookies) or "").strip()
    if ua:
        payload["ua"] = ua
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def award_scene(
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
    """领取任务奖励（scene.award），返回完整 mtop 响应。"""
    data = build_award_data(item, cookies=cookies, ua_builder=ua_builder)
    return mtop_get(
        cookies,
        "mtop.taobao.pentaprism.scene.award",
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
            "callback": "mtopjsonp10",
        },
    )


def award_coin_amount(payload: dict) -> str:
    """从 award 响应中解析实际发放金币数。"""
    model = ((payload or {}).get("data") or {}).get("model") or {}
    rewards = model.get("rewards") or []
    if not rewards:
        return "-"
    result = rewards[0].get("result") or {}
    return str(
        result.get("displayFinalCount")
        or result.get("finalCount")
        or result.get("displayBaseCount")
        or result.get("baseCount")
        or "-"
    )


def build_click_goods_data(item: dict) -> str:
    """构造 clickGoodsAd 请求 data。"""
    params = resolve_task_params(item)
    delivery_id = str(params.get("deliveryId") or item.get("id") or "")
    impl_id = str(params.get("implId") or "")
    if not delivery_id or not impl_id:
        raise RuntimeError(f"任务缺少 taskParams：{task_title(item)}")
    payload = {
        "sceneId": str(params.get("sceneId") or DEFAULT_TAO_COIN_SCENE_ID),
        "deliveryId": delivery_id,
        "implId": impl_id,
        "asac": str(params.get("asac") or DEFAULT_CLICK_GOODS_ASAC),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def click_goods_ad(
        cookies: dict,
        item: dict,
        *,
        session: requests.Session,
        page_url: str = DEFAULT_PRODUCT_TASK_URL,
        referer: str = DEFAULT_REFERER,
        timeout: int = 20,
        proxies: dict | None = None,
) -> dict:
    """
    点击/逛商品计次（mtop.taobao.pc.growth.clickGoodsAd）。
    不需要 itemId；同一任务参数调用 N 次即可推进进度。
    """
    data = build_click_goods_data(item)
    params = resolve_task_params(item)
    asac = str(params.get("asac") or DEFAULT_CLICK_GOODS_ASAC)
    return mtop_get(
        cookies,
        "mtop.taobao.pc.growth.clickGoodsAd",
        data,
        session=session,
        referer=referer,
        timeout=timeout,
        proxies=proxies,
        extra_params={
            "type": "originaljsonp",
            "valueType": "original",
            "responseType": "ORIGINAL_JSON",
            "timeout": "20000",
            "asac": asac,
            "callback": "mtopjsonp11",
            "pageUrl": page_url,
        },
    )


def click_goods_ok(payload: dict) -> bool:
    if not ret_ok(payload):
        return False
    data = (payload or {}).get("data") or {}
    if data.get("data") is True or data.get("code") in (200, "200"):
        return True
    return str(data.get("message") or "").upper() == "OK"


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
    _sleep_after_request("visit_task_url")
    if duration > 0:
        time.sleep(duration)
    return response.status_code


def iter_pending_jump_tasks(data: dict) -> list[dict]:
    model = (data or {}).get("model") or []
    return [item for item in model if is_jump_task(item) and is_task_pending(item)]


def iter_pending_click_goods_tasks(data: dict) -> list[dict]:
    model = (data or {}).get("model") or []
    return [
        item for item in model if is_click_goods_task(item) and is_task_pending(item)
    ]


def iter_claimable_tasks(data: dict) -> list[dict]:
    model = (data or {}).get("model") or []
    return [item for item in model if is_task_claimable(item)]
