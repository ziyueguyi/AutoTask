# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_task.py
# @文件介绍 :淘宝淘金币任务列表 / 任务推进（query + scene.trigger）
# 青龙环境变量（前缀 TX_TASK）：
#   TX_TASK_account  Cookie
#   TX_TASK_notify   通知开关，填 1 开启
# 依赖：curl_cffi；任务逻辑见 tools/pentaprism_task.py
const $ = new Env('淘金币任务')
cron: 15 9,21 * * *
"""
import os
import random
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests


class TxTask:
    SCENE_ID = "8676"
    ASAC = "2A24A178YUFG02XVGJNZFM"
    PAGE_URL = "https://huodong.taobao.com/wow/z/tbhome/pc-growth/tao-coin"
    PAGE_REFERER = "https://huodong.taobao.com/"

    def __init__(self) -> None:
        script_dir = Path(__file__).resolve().parent
        public_path = script_dir.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("TX_TASK")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")

        task_spc = util.spec_from_file_location(
            "pentaprism_task",
            str(script_dir / "tools" / "pentaprism_task.py"),
        )
        self.task_api = util.module_from_spec(task_spc)
        task_spc.loader.exec_module(self.task_api)

        self.session = requests.Session(timeout=20)
        proxy = (os.getenv(self.initialize.env_key("proxy")) or "").strip()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": self.PAGE_REFERER,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        })

    def load_account_list(self):
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(
                f"未配置环境变量 {self.env_name}，请在青龙面板配置 Cookie",
                is_flag=True,
            )
        return accounts

    def run(self) -> None:
        self.initialize.info_message("TX Task start")
        accounts = self.load_account_list()
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}")
            try:
                cookies = self.cookies_to_dict(account)
                if not cookies:
                    self.initialize.error_message(f"{account_name} Cookie 为空", is_flag=True)
                else:
                    nick = cookies.get("tracknick") or cookies.get("lgc") or account_name
                    self.do_work(nick, cookies)
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True)
            if index < len(accounts):
                delay = random.uniform(2, 5)
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message("TX Task end")
        self.initialize.send_notify("TX Task | https://huodong.taobao.com/")

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
            return TxTask.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    def query_tasks(self, cookies: dict) -> dict:
        return self.task_api.query_scene(
            cookies,
            self.SCENE_ID,
            asac=self.ASAC,
            page_url=self.PAGE_URL,
            session=self.session,
            referer=self.PAGE_REFERER,
        )

    def print_tasks(self, nick: str, data: dict) -> None:
        api = self.task_api
        model = (data or {}).get("model") or []
        finish = (data or {}).get("finishCount", "?")
        total = (data or {}).get("totalCount") or len(model)
        self.initialize.info_message(f"{nick} 任务进度：{finish}/{total}", is_flag=True)
        for index, item in enumerate(model, 1):
            self.initialize.info_message(
                f"{nick} [{index}] {api.task_title(item)} | {api.task_status(item)} | "
                f"金币 {api.task_coin(item)} | {api.task_url(item)}",
                is_flag=True,
            )

    def do_jump_tasks(self, nick: str, cookies: dict, data: dict) -> None:
        api = self.task_api
        pending = api.iter_pending_jump_tasks(data)
        if not pending:
            self.initialize.info_message(f"{nick} 无可自动完成的跳转任务", is_flag=True)
            return
        for item in pending:
            title = api.task_title(item)
            try:
                params = api.resolve_task_params(item)
                self.initialize.info_message(
                    f"{nick} 触发任务：{title} | deliveryId={params.get('deliveryId')} "
                    f"| implId={params.get('implId')}",
                    is_flag=True,
                )
                result = api.trigger_scene(
                    cookies,
                    item,
                    session=self.session,
                    page_url=self.PAGE_URL,
                    referer=self.PAGE_REFERER,
                    ua_builder=api.build_risk_ua,
                )
                if not api.ret_ok(result):
                    self.initialize.error_message(
                        f"{nick} {title} trigger 失败：{api.ret_msg(result)}",
                        is_flag=True,
                    )
                    continue
                model_data = (result.get("data") or {}).get("model") or {}
                status = model_data.get("status") or ((model_data.get("progress") or {}).get("status"))
                self.initialize.info_message(
                    f"{nick} {title} trigger 成功 status={status}",
                    is_flag=True,
                )
                url = api.task_url(model_data) if model_data else api.task_url(item)
                if url and url != "-":
                    duration = int((item.get("assets") or {}).get("duration") or 0)
                    http_status = api.visit_task_url(
                        cookies,
                        url,
                        session=self.session,
                        referer=self.PAGE_URL,
                        duration=duration,
                    )
                    self.initialize.info_message(
                        f"{nick} {title} 访问任务页 HTTP {http_status}"
                        + (f"（停留 {duration}s）" if duration else ""),
                        is_flag=True,
                    )
            except Exception as exc:
                self.initialize.error_message(f"{nick} {title} 执行失败：{exc}", is_flag=True)
            time.sleep(random.uniform(1.5, 3.0))

    def do_work(self, nick: str, cookies: dict) -> None:
        api = self.task_api
        tasks = self.query_tasks(cookies)
        if not api.ret_ok(tasks):
            self.initialize.error_message(f"{nick} 任务查询失败：{api.ret_msg(tasks)}", is_flag=True)
            return
        task_data = tasks.get("data") or {}
        self.print_tasks(nick, task_data)
        self.do_jump_tasks(nick, cookies, task_data)
        tasks_after = self.query_tasks(cookies)
        if api.ret_ok(tasks_after):
            self.initialize.info_message(f"{nick} —— 触发后任务列表 ——", is_flag=True)
            self.print_tasks(nick, tasks_after.get("data") or {})


if __name__ == "__main__":
    TaoJinBiTask().run()
