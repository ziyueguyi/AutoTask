# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_jh_exchange.py
# @文件介绍 :淘江湖红包兑换（benefit 列表 + 余额校验；兑换动作待抓包）
# 青龙环境变量（前缀 TX）：
#   TX_account            Cookie（淘系共用）
#   TX_notify             通知开关，填 1 开启
#   TX_JH_EXCHANGE_range  兑换范围（按 costCoin），默认 -1
#                        -1 / 100-1000 / 100- / -1000
# 依赖：curl_cffi
const $ = new Env('淘江湖兑换')
cron: 1 1 1 1 1
"""
import hashlib
import json
import os
import random
import sys
import time
from importlib import util
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxJhExchange(Base):
    APP_KEY = "12574478"
    HOST = "https://h5api.m.taobao.com"

    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH"])
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": "https://jianghu.taobao.com/coin.html",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        })
        self.coin_range = self.parse_coin_range(
            (os.getenv("TX_JH_EXCHANGE_range") or "-1").strip()
        )
        self.h5_token = self.load_tool("h5_token", "h5_token.py")
        self.initialize.info_message(f"兑换范围：{self.format_coin_range(self.coin_range)}")

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
            return TxJhExchange.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    @staticmethod
    def account_nick(cookies: dict, fallback: str = "") -> str:
        for key in ("tracknick", "lgc", "_nk_", "dnk", "unb"):
            val = (cookies.get(key) or "").strip()
            if val:
                return unquote(val)
        return fallback

    def run(self) -> None:
        task_name = "TX JH Exchange"
        notify_title = "TX JH Exchange | https://jianghu.taobao.com/coin.html"
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

    def mtop_sign_params(self, cookies: dict, data: str, flag: bool = True) -> tuple[str, str]:
        token = str(cookies.get("_m_h5_tk", "")).split("_", 1)[0]
        if not token and flag:
            self.h5_token.ensure_m_h5_tk(
                self.session,
                cookies,
                on_ok=self.initialize.info_message,
                on_err=self.initialize.error_message,
            )
            return self.mtop_sign_params(cookies, data, flag=False)
        if not token:
            raise RuntimeError("Cookie 缺少 _m_h5_tk，且自动获取失败")
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
        time.sleep(random.uniform(1.0, 5.0))
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
        time.sleep(random.uniform(1.0, 5.0))
        text = (response.text or "").strip()
        try:
            return self.parse_jsonp(text)
        except Exception:
            return json.loads(text)

    # —— 兑换范围 ——
    @staticmethod
    def parse_coin_range(raw: str) -> tuple[int | None, int | None] | None:
        """
        解析兑换范围，返回 (min, max)；None 表示该端不限。
        返回 None（整体）表示 -1 不限全部。
        """
        text = (raw or "-1").strip()
        if text == "-1":
            return None
        if "-" not in text:
            raise ValueError(
                f"兑换范围格式错误：{raw!r}，支持 -1 / 100-1000 / 100- / -1000"
            )
        left, right = text.split("-", 1)
        if left == "" and right == "":
            raise ValueError(f"兑换范围格式错误：{raw!r}")
        low = int(left) if left else None
        high = int(right) if right else None
        if low is not None and high is not None and low > high:
            raise ValueError(f"兑换范围下限大于上限：{raw!r}")
        return low, high

    @staticmethod
    def format_coin_range(coin_range: tuple[int | None, int | None] | None) -> str:
        if coin_range is None:
            return "-1（不限）"
        low, high = coin_range
        if low is None and high is None:
            return "-1（不限）"
        if low is None:
            return f"-{high}（≤ {high}）"
        if high is None:
            return f"{low}-（≥ {low}）"
        return f"{low}-{high}"

    @staticmethod
    def benefit_coin_cost(item: dict) -> int | None:
        raw = item.get("costCoin")
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            try:
                return int(float(raw))
            except (TypeError, ValueError):
                return None

    @staticmethod
    def cost_coin_type(item: dict) -> str:
        props = item.get("properties") or {}
        return str(props.get("costCoinType") or "tao_coin")

    @staticmethod
    def is_tao_coin_cost(item: dict) -> bool:
        return TxJhExchange.cost_coin_type(item) == "tao_coin"

    def in_coin_range(self, cost: int | None) -> bool:
        if self.coin_range is None:
            return True
        if cost is None:
            return False
        low, high = self.coin_range
        if low is not None and cost < low:
            return False
        if high is not None and cost > high:
            return False
        return True

    def filter_benefits_by_range(self, benefits: list) -> list:
        result = []
        for item in benefits:
            if not self.is_tao_coin_cost(item):
                continue
            if self.in_coin_range(self.benefit_coin_cost(item)):
                result.append(item)
        return result

    @staticmethod
    def benefit_label(item: dict) -> str:
        title = item.get("title") or item.get("benefitDesc") or ""
        amount = f"{item.get('displayAmount', '-')}{item.get('displayAmountUnit', '')}"
        return f"{title}({amount})" if title else amount

    # —— 淘江湖兑换列表 ——
    def query_jianghu_benefits(self, cookies: dict) -> dict:
        return self.mtop_get(cookies, "mtop.taobao.bbs.coin.benefit.get", "{}", {
            "valueType": "original",
            "jsonpIncPrefix": "tbbe",
            "type": "originaljsonp",
            "callback": "mtopjsonptbbe4",
        })

    @staticmethod
    def extract_red_packet_list(payload: dict) -> list:
        outer = (payload or {}).get("data") or {}
        inner = outer.get("data") if isinstance(outer.get("data"), dict) else outer
        return (inner or {}).get("redPacketList") or []

    def print_benefits(self, nick: str, benefits: list, balance: int | None = None) -> list:
        if not benefits:
            self.initialize.info_message(f"{nick} JH exchange: 暂无红包", is_flag=True)
            return []
        matched = self.filter_benefits_by_range(benefits)
        self.initialize.info_message(
            f"{nick} JH exchange (共 {len(benefits)} 个，淘金币范围内 {len(matched)} 个）：",
            is_flag=True,
        )
        for index, item in enumerate(benefits, 1):
            label = self.benefit_label(item)
            cost = item.get("costCoin", "-")
            cost_type = self.cost_coin_type(item)
            stock = "有货" if item.get("hasInventory") else "无货"
            cost_num = self.benefit_coin_cost(item)
            if cost_type != "tao_coin":
                tag = f"非淘金币({cost_type})"
            elif not self.in_coin_range(cost_num):
                tag = "范围外"
            elif balance is None:
                tag = "范围内"
            elif cost_num is not None and balance >= cost_num:
                tag = "可兑" if item.get("hasInventory") else "可兑(无货)"
            else:
                tag = "余额不足"
            self.initialize.info_message(
                f"{nick} [{index}] {label} | 消耗 {cost} | {stock} | {tag}",
                is_flag=True,
            )
        return matched

    def try_exchange(self, nick: str, cookies: dict, item: dict, balance: int) -> bool | None:
        """
        兑换动作待抓包。
        返回 True=成功，False=跳过/失败，None=余额够但接口未接入（占位）。
        """
        cost = self.benefit_coin_cost(item)
        label = self.benefit_label(item)
        if not self.is_tao_coin_cost(item):
            self.initialize.info_message(f"{nick} 跳过 {label}：非淘金币消耗", is_flag=True)
            return False
        if cost is None:
            self.initialize.error_message(f"{nick} {label} 缺少 costCoin，跳过", is_flag=True)
            return False
        if not item.get("hasInventory"):
            self.initialize.info_message(f"{nick} 跳过 {label}：无库存", is_flag=True)
            return False
        if balance < cost:
            self.initialize.info_message(
                f"{nick} 跳过 {label}：余额 {balance} < 所需 {cost}",
                is_flag=True,
            )
            return False
        # TODO: 接入真实兑换/抽奖 mtop 后在此调用，成功返回 True
        self.initialize.info_message(
            f"{nick} 余额充足（{balance} ≥ {cost}），待兑换：{label} "
            f"benefitCode={item.get('benefitCode')}（接口待抓包）",
            is_flag=True,
        )
        return None

    def do_work(self, nick: str, cookies: dict) -> None:
        self.h5_token.ensure_m_h5_tk(
            self.session,
            cookies,
            on_ok=self.initialize.info_message,
            on_err=self.initialize.error_message,
        )
        query_taocoin = self.load_tool("query_taocoin", "query_taocoin.py")
        coin = query_taocoin.query_user_taocoin(cookies, session=self.session)
        if not coin.get("ok"):
            self.initialize.error_message(
                f"{nick} 淘金币余额查询失败：{coin.get('message')}",
                is_flag=True,
            )
            return
        balance = coin.get("coin_amount")
        saving = coin.get("coin_saving", "-")
        if balance is None:
            self.initialize.error_message(f"{nick} 未读到 coinAmount，跳过兑换", is_flag=True)
            return
        self.initialize.info_message(
            f"{nick} 当前淘金币余额 {balance}（约 {saving} 元）",
            is_flag=True,
        )

        benefit_resp = self.query_jianghu_benefits(cookies)
        if not self.ret_ok(benefit_resp):
            self.initialize.error_message(
                f"{nick} JH benefit list failed：{self.ret_msg(benefit_resp)}",
                is_flag=True,
            )
            return
        benefits = self.extract_red_packet_list(benefit_resp)
        matched = self.print_benefits(nick, benefits, balance=balance)
        if not matched:
            self.initialize.info_message(f"{nick} 范围内无可兑换红包", is_flag=True)
            return

        remain = balance
        exchanged = 0
        skipped = 0
        pending = 0
        for item in matched:
            cost = self.benefit_coin_cost(item)
            if cost is None or remain < cost:
                skipped += 1
                label = self.benefit_label(item)
                self.initialize.info_message(
                    f"{nick} 跳过 {label}：余额 {remain} < 所需 {cost if cost is not None else '?'}",
                    is_flag=True,
                )
                continue
            if not item.get("hasInventory"):
                skipped += 1
                self.initialize.info_message(
                    f"{nick} 跳过 {self.benefit_label(item)}：无库存",
                    is_flag=True,
                )
                continue
            result = self.try_exchange(nick, cookies, item, remain)
            if result is True:
                remain -= cost
                exchanged += 1
            elif result is None:
                pending += 1
            else:
                skipped += 1
        self.initialize.info_message(
            f"{nick} 兑换结束：成功 {exchanged}，待接入 {pending}，跳过 {skipped}，余额 {remain}",
            is_flag=True,
        )


if __name__ == "__main__":
    TxJhExchange().run()
