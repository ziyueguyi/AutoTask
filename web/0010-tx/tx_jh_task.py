# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_jh_task.py
# @文件介绍 :淘江湖任务（sceneId=8244）
# 青龙环境变量（前缀 TX）：
#   TX_account  Cookie（淘系共用）
#   TX_notify   通知开关，填 1 开启
# 依赖：curl_cffi
const $ = new Env('淘江湖任务')
cron: 1 1 1 1 1
"""
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxJhTask(Base):
    REFERER = "https://jianghu.taobao.com/coin.html"
    APP_KEY = "12574478"
    HOST = "https://h5api.m.taobao.com"

    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH"])
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": self.REFERER,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        })

    @staticmethod
    def cookies_to_dict(account: dict) -> dict:
        raw = account.get("cookie") or account.get("Cookie") or ""
        if raw:
            result = {}
            for part in str(raw).split(";"):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    result[key.strip()] = value.strip()
            return result
        if account.get("token") and len(account) == 1:
            return TxJhTask.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    @staticmethod
    def account_nick(cookies: dict, fallback: str = "") -> str:
        for key in ("tracknick", "lgc", "_nk_", "dnk", "unb"):
            val = (cookies.get(key) or "").strip()
            if val:
                return unquote(val)
        return fallback

    def run(self) -> None:
        task_name = "TX JH Task"
        notify_title = "TX JH Task | https://jianghu.taobao.com/coin.html"
        self.initialize.info_message(f"{task_name} start")
        accounts = self.initialize.load_accounts()
        if not accounts:
            env_name = self.initialize.env_key("account")
            self.initialize.error_message(
                f"未配置环境变量 {env_name}，请在青龙面板配置 Cookie",
                is_flag=True,
            )
            self.initialize.send_notify(notify_title)
            return
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(
                f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}"
            )
            try:
                cookies = self.cookies_to_dict(account)
                if not cookies:
                    self.initialize.error_message(
                        f"{account_name} Cookie 为空", is_flag=True
                    )
                else:
                    nick = self.account_nick(cookies, account_name)
                    self.do_work(nick, cookies)
            except Exception as exc:
                self.initialize.error_message(
                    f"{account_name} 执行失败：{exc}", is_flag=True
                )
            if index < len(accounts):
                delay = random.uniform(2.0, 5.0)
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message(f"{task_name} end")
        self.initialize.send_notify(notify_title)

    @staticmethod
    def parse_jsonp(text: str) -> dict:
        text = (text or "").strip()
        if text.startswith("mtopjsonp") and "(" in text:
            text = text[text.find("(") + 1: text.rfind(")")]
        return json.loads(text)

    @staticmethod
    def ret_ok(payload: dict) -> bool:
        ret = payload.get("ret") or []
        return bool(ret) and str(ret[0]).startswith("SUCCESS")

    @staticmethod
    def ret_msg(payload: dict) -> str:
        ret = payload.get("ret") or []
        return str(ret[0]) if ret else "未知错误"

    def mtop_sign_params(self, cookies: dict, data: str) -> tuple[str, str]:
        token = str(cookies.get("_m_h5_tk", "")).split("_", 1)[0]
        if not token:
            raise RuntimeError("Cookie 缺少 _m_h5_tk")
        t = str(int(time.time() * 1000))
        sign = hashlib.md5(f"{token}&{t}&{self.APP_KEY}&{data}".encode()).hexdigest()
        return t, sign

    def mtop_get(self, cookies: dict, api: str, data: str, extra_params: dict | None = None) -> dict:
        t, sign = self.mtop_sign_params(cookies, data)
        params = {
            "jsv": "2.5.1",
            "appKey": self.APP_KEY,
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
        url = f"{self.HOST}/h5/{api}/1.0/"
        response = self.session.get(url, params=params, cookies=cookies)
        return self.parse_jsonp(response.text)

    def mtop_post(
        self,
        cookies: dict,
        api: str,
        data: str,
        extra_params: dict | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        t, sign = self.mtop_sign_params(cookies, data)
        params = {
            "jsv": "2.5.1",
            "appKey": self.APP_KEY,
            "t": t,
            "sign": sign,
            "v": "1.0",
            "timeout": "5000",
            "dataType": "jsonp",
            "valueType": "original",
            "jsonpIncPrefix": "tbbe",
            "api": api,
            "type": "originaljson",
        }
        if extra_params:
            params.update(extra_params)
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://huodong.taobao.com",
            "asac": "undefined",
        }
        if extra_headers:
            headers.update(extra_headers)
        url = f"{self.HOST}/h5/{api}/1.0/"
        response = self.session.post(
            url,
            params=params,
            data={"data": data},
            cookies=cookies,
            headers=headers,
        )
        text = (response.text or "").strip()
        try:
            return self.parse_jsonp(text)
        except Exception:
            return json.loads(text)

    # —— 淘江湖任务（sceneId=8244） ——
    def query_tasks(self, cookies: dict) -> dict:
        return self.mtop_get(
            cookies,
            "mtop.taobao.pentaprism.scene.query",
            '{"sceneId":"8244"}',
            {
                "type": "jsonp",
                "timeout": "10000",
                "pageUrl": "https://jianghu.taobao.com/coin.html",
                "preventFallback": "true",
                "callback": "mtopjsonp7",
            },
        )

    @staticmethod
    def task_title(item: dict) -> str:
        assets = item.get("assets") or {}
        if assets.get("title"):
            return str(assets["title"])
        center = ((item.get("theme") or {}).get("center") or {})
        if center.get("processTitle"):
            return str(center["processTitle"])
        for sub in item.get("subList") or []:
            title = TxJhTask.task_title(sub)
            if title and not title.startswith("任务"):
                return title
        return f"任务{item.get('id', '?')}"

    @staticmethod
    def task_status(item: dict) -> str:
        if str(item.get("complete")).lower() == "true":
            return "已完成"
        prog = item.get("progress") or {}
        status = prog.get("status") or item.get("status") or "未知"
        times = prog.get("times", "0")
        need = prog.get("needTimes", "1")
        mapping = {"ACCEPTED": "待完成", "COMPLETED": "已完成", "COMPLETE": "已完成", "AWARD": "待领取"}
        return f"{mapping.get(status, status)}({times}/{need})"

    @staticmethod
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

    @staticmethod
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
            url = TxJhTask.task_url(sub)
            if url and url != "-":
                return url
        return "-"

    def print_tasks(self, nick: str, data: dict) -> None:
        model = (data or {}).get("model") or []
        finish = (data or {}).get("finishCount", "?")
        total = (data or {}).get("totalCount") or len(model)
        self.initialize.info_message(f"{nick} JH task progress：{finish}/{total}", is_flag=True)
        for index, item in enumerate(model, 1):
            self.initialize.info_message(
                f"{nick} [{index}] {self.task_title(item)} | {self.task_status(item)} | "
                f"金币 {self.task_coin(item)} | {self.task_url(item)}",
                is_flag=True,
            )

    def visit_task_url(self, cookies: dict, url: str, duration: int = 0) -> int:
        if not url or url == "-":
            raise RuntimeError("任务 URL 为空")
        response = self.session.get(
            url,
            cookies=cookies,
            headers={
                "referer": self.REFERER,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            allow_redirects=True,
        )
        if duration > 0:
            time.sleep(duration)
        return response.status_code

    def visit_incomplete_jump_tasks(self, nick: str, cookies: dict, data: dict, limit: int = 5) -> None:
        """访问未完成的跳转类任务页（task_jump / 有 action URL）。"""
        visited = 0
        for item in (data or {}).get("model") or []:
            if visited >= limit:
                break
            if str(item.get("complete")).lower() == "true":
                continue
            task_type = str(item.get("taskType") or "")
            url = self.task_url(item)
            if not url.startswith("http"):
                continue
            if task_type not in ("task_jump", "system_task_customize", "") and "jump" not in task_type:
                # 仍允许有明确 action 的浏览类任务
                assets = item.get("assets") or {}
                if not assets.get("action"):
                    continue
            title = self.task_title(item)
            self.initialize.info_message(f"{nick} 访问任务页：{title} → {url}", is_flag=True)
            try:
                status = self.visit_task_url(cookies, url)
                self.initialize.info_message(f"{nick} {title} 访问结束 HTTP {status}", is_flag=True)
            except Exception as exc:
                self.initialize.error_message(f"{nick} {title} 访问失败：{exc}", is_flag=True)
            visited += 1
            time.sleep(random.uniform(1.5, 3.0))
        if visited == 0:
            self.initialize.info_message(f"{nick} 无待访问的跳转任务", is_flag=True)

    def do_work(self, nick: str, cookies: dict) -> None:
        tasks = self.query_tasks(cookies)
        if not self.ret_ok(tasks):
            self.initialize.error_message(f"{nick} JH task query failed：{self.ret_msg(tasks)}", is_flag=True)
            return
        task_data = tasks.get("data") or {}
        self.print_tasks(nick, task_data)
        self.visit_incomplete_jump_tasks(nick, cookies, task_data)


if __name__ == "__main__":
    TxJhTask().run()
