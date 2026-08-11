# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_jh_task.py
# @文件介绍 :淘江湖任务（sceneId=8244：query + trigger/clickGoodsAd + award）
# 青龙环境变量（前缀 TX / TX_JH）：
#   TX_account  Cookie（淘系共用）
#   TX_notify   通知开关，填 1 开启
# 依赖：curl_cffi；任务逻辑见 tools/pentaprism_task.py
const $ = new Env('淘江湖任务')
cron: 1 1 1 1 1
"""
import random
import sys
import time
from importlib import util
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxJhTask(Base):
    REFERER = "https://jianghu.taobao.com/"
    PAGE_URL = "https://jianghu.taobao.com/coin.html"
    SCENE_ID = "8244"
    # 仅查询展示、不自动执行/领取（需真人互动）
    # 说明：「聊天室」抓包确认 trigger 即可进 AWARDING，可自动；投票仍需真投。
    SKIP_EXECUTE_TITLES = (
        "参与投票",
        "发布投票",
        "投票",
        "回复",
        "发布",
        "邀请",
        "助力",
    )
    # 帖子任务完成后常会轮换补出新任务，多轮补跑
    MAX_EXECUTE_ROUNDS = 3

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
        self.task_api = self.load_tool("pentaprism_task", "pentaprism_task.py")
        self.h5_token = self.load_tool("h5_token", "h5_token.py")

    def load_tool(self, module_name: str, filename: str):
        path = Path(__file__).resolve().parent / "tools" / filename
        spec = util.spec_from_file_location(module_name, str(path))
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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
                delay = random.uniform(1.0, 5.0)
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message(f"{task_name} end")
        self.initialize.send_notify(notify_title)

    @staticmethod
    def section_banner(title: str, width: int = 30) -> str:
        body = f" {title} "
        pad = max(width - len(body), 6)
        left = pad // 2
        right = pad - left
        return f"{'=' * left}{body}{'=' * right}"

    def should_skip_execute(self, title: str) -> bool:
        text = (title or "").strip()
        return any(key in text for key in self.SKIP_EXECUTE_TITLES)

    def query_tasks(self, cookies: dict) -> dict:
        api = self.task_api
        return api.query_scene(
            cookies,
            self.SCENE_ID,
            asac=None,
            page_url=self.PAGE_URL,
            session=self.session,
            referer=self.REFERER,
        )

    def print_tasks(self, nick: str, data: dict) -> None:
        api = self.task_api
        model = (data or {}).get("model") or []
        finish = (data or {}).get("finishCount", "?")
        total = (data or {}).get("totalCount") or len(model)
        self.initialize.info_message(f"{nick} JH 任务进度：{finish}/{total}", is_flag=True)
        for index, item in enumerate(model, 1):
            title = api.task_title(item)
            flag = " | 仅展示" if self.should_skip_execute(title) else ""
            self.initialize.info_message(
                f"{nick} [{index}] {title} | {api.task_status(item)} | "
                f"金币 {api.task_coin(item)} | {api.task_url(item)}{flag}",
                is_flag=True,
            )

    def do_click_goods_tasks(self, nick: str, cookies: dict, data: dict) -> None:
        api = self.task_api
        pending = api.iter_pending_click_goods_tasks(data)
        if not pending:
            self.initialize.info_message(f"{nick} 无可自动完成的逛商品任务", is_flag=True)
            return
        for item in pending:
            title = api.task_title(item)
            if self.should_skip_execute(title):
                self.initialize.info_message(f"{nick} 跳过执行（仅展示）：{title}", is_flag=True)
                continue
            try:
                params = api.resolve_task_params(item)
                need = api.click_goods_need_times(item)
                remain = api.click_goods_remain_times(item) or need
                self.initialize.info_message(
                    f"{nick} 逛商品：{title} | 需点击 {remain}/{need} 次"
                    f" | deliveryId={params.get('deliveryId')} | implId={params.get('implId')}",
                    is_flag=True,
                )
                ok_count = 0
                for i in range(1, remain + 1):
                    result = api.click_goods_ad(
                        cookies,
                        item,
                        session=self.session,
                        page_url=api.DEFAULT_PRODUCT_TASK_URL,
                        referer=self.REFERER,
                    )
                    if not api.click_goods_ok(result):
                        self.initialize.error_message(
                            f"{nick} {title} 第{i}次 clickGoodsAd 失败："
                            f"{api.ret_msg(result)} | {(result.get('data') or {})}",
                            is_flag=True,
                        )
                        break
                    ok_count += 1
                    self.initialize.info_message(
                        f"{nick} {title} 第{i}/{remain} 次点击成功",
                        is_flag=True,
                    )
                self.initialize.info_message(
                    f"{nick} {title} 逛商品完成 {ok_count}/{remain}",
                    is_flag=True,
                )
            except Exception as exc:
                self.initialize.error_message(f"{nick} {title} 逛商品失败：{exc}", is_flag=True)

    def do_jump_tasks(self, nick: str, cookies: dict, data: dict) -> None:
        """跳转/浏览类：scene.trigger + 访问 action URL（如「浏览淘金币频道」）。"""
        api = self.task_api
        pending = api.iter_pending_jump_tasks(data)
        if not pending:
            self.initialize.info_message(f"{nick} 无可自动完成的跳转任务", is_flag=True)
            return
        for item in pending:
            title = api.task_title(item)
            if self.should_skip_execute(title):
                self.initialize.info_message(f"{nick} 跳过执行（仅展示）：{title}", is_flag=True)
                continue
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
                    referer=self.REFERER,
                    ua_builder=api.build_risk_ua,
                )
                if not api.ret_ok(result):
                    self.initialize.error_message(
                        f"{nick} {title} trigger 失败：{api.ret_msg(result)}",
                        is_flag=True,
                    )
                    continue
                model_data = (result.get("data") or {}).get("model") or {}
                status = model_data.get("status") or (
                    (model_data.get("progress") or {}).get("status")
                )
                self.initialize.info_message(
                    f"{nick} {title} trigger 成功 status={status}",
                    is_flag=True,
                )
                if status not in {"AWARDING", "AWARD", "COMPLETE", "COMPLETED"}:
                    self.initialize.info_message(
                        f"{nick} {title} trigger 后未进入可领状态，"
                        f"可能还需页面内真实操作（如投票/聊天）",
                        is_flag=True,
                    )
                url = api.task_url(model_data) if model_data else api.task_url(item)
                if url and url != "-":
                    duration = int((item.get("assets") or {}).get("duration") or 0)
                    # 「浏览淘金币频道」抓包无 duration，仍访问落地页，稍作停留
                    if not duration and "tao-coin" in url:
                        duration = random.randint(2, 5)
                    http_status = api.visit_task_url(
                        cookies,
                        url,
                        session=self.session,
                        referer=self.PAGE_URL,
                        duration=duration,
                    )
                    self.initialize.info_message(
                        f"{nick} {title} 访问任务页 HTTP {http_status}"
                        + (f"（页面停留 {duration}s）" if duration else ""),
                        is_flag=True,
                    )
            except Exception as exc:
                self.initialize.error_message(f"{nick} {title} 执行失败：{exc}", is_flag=True)

    def do_claim_awards(self, nick: str, cookies: dict, data: dict) -> None:
        api = self.task_api
        claimable = api.iter_claimable_tasks(data)
        if not claimable:
            self.initialize.info_message(f"{nick} 无可领取任务奖励", is_flag=True)
            return
        self.initialize.info_message(
            f"{nick} 开始统一领取，共 {len(claimable)} 个待领奖任务",
            is_flag=True,
        )
        for item in claimable:
            title = api.task_title(item)
            if self.should_skip_execute(title):
                self.initialize.info_message(f"{nick} 跳过领取（仅展示）：{title}", is_flag=True)
                continue
            try:
                params = api.resolve_task_params(item)
                self.initialize.info_message(
                    f"{nick} 领取：{title} | deliveryId={params.get('deliveryId')} "
                    f"| implId={params.get('implId')}",
                    is_flag=True,
                )
                result = api.award_scene(
                    cookies,
                    item,
                    session=self.session,
                    page_url=self.PAGE_URL,
                    referer=self.REFERER,
                    ua_builder=api.build_risk_ua,
                )
                if not api.ret_ok(result):
                    self.initialize.error_message(
                        f"{nick} {title} 领取失败：{api.ret_msg(result)}",
                        is_flag=True,
                    )
                    continue
                coin = api.award_coin_amount(result)
                model = (result.get("data") or {}).get("model") or {}
                status = model.get("status") or ((model.get("progress") or {}).get("status"))
                self.initialize.info_message(
                    f"{nick} {title} 领取成功 +{coin} 淘金币 status={status}",
                    is_flag=True,
                )
            except Exception as exc:
                self.initialize.error_message(f"{nick} {title} 领取异常：{exc}", is_flag=True)

    def count_auto_actions(self, data: dict) -> tuple[int, int, int]:
        api = self.task_api
        clicks = [
            i for i in api.iter_pending_click_goods_tasks(data)
            if not self.should_skip_execute(api.task_title(i))
        ]
        jumps = [
            i for i in api.iter_pending_jump_tasks(data)
            if not self.should_skip_execute(api.task_title(i))
        ]
        claims = [
            i for i in api.iter_claimable_tasks(data)
            if not self.should_skip_execute(api.task_title(i))
        ]
        return len(clicks), len(jumps), len(claims)

    def do_work(self, nick: str, cookies: dict) -> None:
        self.h5_token.ensure_m_h5_tk(
            self.session,
            cookies,
            on_ok=self.initialize.info_message,
            on_err=self.initialize.error_message,
        )
        api = self.task_api

        self.initialize.info_message(self.section_banner("任务查询"), is_flag=True)
        tasks = self.query_tasks(cookies)
        if not api.ret_ok(tasks):
            self.initialize.error_message(
                f"{nick} JH 任务查询失败：{api.ret_msg(tasks)}", is_flag=True
            )
            return
        task_data = tasks.get("data") or {}
        self.print_tasks(nick, task_data)

        self.initialize.info_message(self.section_banner("任务执行"), is_flag=True)
        for round_no in range(1, self.MAX_EXECUTE_ROUNDS + 1):
            if round_no > 1:
                tasks = self.query_tasks(cookies)
                if not api.ret_ok(tasks):
                    self.initialize.error_message(
                        f"{nick} 第{round_no}轮查询失败：{api.ret_msg(tasks)}",
                        is_flag=True,
                    )
                    break
                task_data = tasks.get("data") or {}
                n_click, n_jump, n_claim = self.count_auto_actions(task_data)
                if n_click + n_jump + n_claim <= 0:
                    self.initialize.info_message(
                        f"{nick} 第{round_no}轮无新的可自动任务，结束补跑",
                        is_flag=True,
                    )
                    break
                self.initialize.info_message(
                    f"{nick} 第{round_no}轮补跑（轮换帖子等）"
                    f"：逛商品 {n_click} / 跳转 {n_jump} / 待领 {n_claim}",
                    is_flag=True,
                )
                self.print_tasks(nick, task_data)

            self.do_click_goods_tasks(nick, cookies, task_data)
            self.do_jump_tasks(nick, cookies, task_data)

            tasks_after = self.query_tasks(cookies)
            if not api.ret_ok(tasks_after):
                self.initialize.error_message(
                    f"{nick} 执行后任务查询失败：{api.ret_msg(tasks_after)}",
                    is_flag=True,
                )
                break
            after_data = tasks_after.get("data") or {}
            self.do_claim_awards(nick, cookies, after_data)
            task_data = after_data

        self.initialize.info_message(self.section_banner("结果查询"), is_flag=True)
        tasks_final = self.query_tasks(cookies)
        if api.ret_ok(tasks_final):
            self.print_tasks(nick, tasks_final.get("data") or {})
        else:
            self.initialize.error_message(
                f"{nick} 结果查询失败：{api.ret_msg(tasks_final)}",
                is_flag=True,
            )


if __name__ == "__main__":
    TxJhTask().run()
