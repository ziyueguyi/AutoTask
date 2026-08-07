# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_sign.py
# @文件介绍 :淘宝淘金币签到（查询 → 未签则领取 → 小镇首页）
# 青龙环境变量（前缀 TX / TX_JH）：
#   TX_account  Cookie（淘系共用）
#   TX_notify   通知开关，填 1 开启
# 依赖：curl_cffi
const $ = new Env('淘金币签到')
cron: 15 9,21 * * *
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


class TxSign(Base):
    APP_KEY = "12574478"
    HOST = "https://h5api.m.taobao.com"

    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH"])
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": "https://huodong.taobao.com/",
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
            return TxSign.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    @staticmethod
    def account_nick(cookies: dict, fallback: str = "") -> str:
        for key in ("tracknick", "lgc", "_nk_", "dnk", "unb"):
            val = (cookies.get(key) or "").strip()
            if val:
                return unquote(val)
        return fallback

    def run(self) -> None:
        task_name = "TX Sign"
        notify_title = "TX Sign | https://huodong.taobao.com/"
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

    def sign_calendar(self, cookies: dict) -> dict:
        return self.mtop_get(
            cookies,
            "mtop.coingame.sign.calendar.pure.pc",
            '{"bizCode":"taoCoin","subBizCode":"coinTown"}',
            {
                "valueType": "original",
                "jsonpIncPrefix": "tbbe",
                "type": "originaljsonp",
                "callback": "mtopjsonptbbe1",
            },
        )

    def collect_reward(self, cookies: dict) -> dict:
        return self.mtop_post(
            cookies,
            "mtop.coingame.collect.reward.pc",
            '{"bizCode":"taoCoin","subBizCode":"coinTown","page":"pc"}',
        )

    def town_index(self, cookies: dict) -> dict:
        return self.mtop_get(
            cookies,
            "mtop.coingame.town.index.get.pc",
            '{"bizCode":"taoCoin","subBizCode":"coinTown"}',
            {
                "valueType": "original",
                "jsonpIncPrefix": "tbbe",
                "type": "originaljsonp",
                "callback": "mtopjsonptbbe10",
            },
        )

    @staticmethod
    def calendar_days(data: dict) -> list:
        return (
            ((data or {}).get("model") or {})
            .get("userSign", {})
            .get("signCard", {})
            .get("calendar")
            or []
        )

    @staticmethod
    def today_day(data: dict) -> dict | None:
        for day in TxSign.calendar_days(data):
            if day.get("isToday"):
                return day
        return None

    @staticmethod
    def is_today_signed(data: dict) -> bool:
        today = TxSign.today_day(data)
        return bool(today and today.get("signed"))

    @staticmethod
    def day_summary(day: dict | None, label: str) -> str:
        if not day:
            return f"{label}：无数据"
        signed = "已签" if day.get("signed") else "未签"
        coin = day.get("rewardNumber")
        if coin is None:
            coin = day.get("originRewardNumber", "-")
        return f"{label}（{day.get('dateStr', '?')}）：{signed}，金币 {coin}"

    def print_nearby_sign(self, nick: str, data: dict) -> None:
        calendar = self.calendar_days(data)
        today_idx = next((i for i, d in enumerate(calendar) if d.get("isToday")), -1)
        if today_idx < 0:
            self.initialize.error_message(f"{nick} 未找到今日签到数据", is_flag=True)
            return
        yesterday = calendar[today_idx - 1] if today_idx > 0 else None
        today = calendar[today_idx]
        tomorrow = calendar[today_idx + 1] if today_idx + 1 < len(calendar) else None
        self.initialize.info_message(f"{nick} {self.day_summary(yesterday, '昨天')}", is_flag=True)
        self.initialize.info_message(f"{nick} {self.day_summary(today, '今天')}", is_flag=True)
        self.initialize.info_message(f"{nick} {self.day_summary(tomorrow, '明天')}", is_flag=True)

    def print_coin_total(self, nick: str, data: dict) -> None:
        """推送账号淘金币总量。"""
        model = (data or {}).get("model") or {}
        user = model.get("userInfo") or {}
        display_nick = user.get("userNick") or nick
        coin = user.get("coinAmount", "-")
        self.initialize.info_message(f"{display_nick} 总量，金币 {coin}", is_flag=True)

    def print_collect_result(self, nick: str, data: dict) -> None:
        reward = (data or {}).get("signReward") or {}
        total = (data or {}).get("totalCoinReward") or reward.get("coinReward") or "-"
        name = (data or {}).get("highestPriority") or "签到奖励"
        self.initialize.info_message(f"{nick} 签到成功：{name} +{total} 淘金币", is_flag=True)

    def print_town_index(self, nick: str, data: dict) -> None:
        model = (data or {}).get("model") or {}
        user = model.get("userInfo") or {}
        sign = model.get("userSign") or {}
        activity = model.get("signActivityInfo") or {}
        display_nick = user.get("userNick") or nick
        coin = user.get("coinAmount", "-")
        saving = user.get("coinSaving", "-")
        signed = "已签" if sign.get("signed") else "未签"
        days = (
            (sign.get("signCard") or {}).get("consecutiveSignDays")
            or sign.get("uninterruptedCount")
            or "-"
        )
        progress = activity.get("signProgressDesc") or f"连签{days}天"
        tomorrow = (sign.get("signAward") or {}).get("awardAmount") or (
            (sign.get("signCard") or {}).get("signRewardTomorrow")
        ) or "-"
        self.initialize.info_message(
            f"{display_nick} 余额 {coin}（约 {saving} 元）| 今日{signed} | {progress} | 明日可得 {tomorrow}",
            is_flag=True,
        )

    def do_work(self, nick: str, cookies: dict) -> None:
        calendar = self.sign_calendar(cookies)
        if not self.ret_ok(calendar):
            self.initialize.error_message(f"{nick} 签到查询失败：{self.ret_msg(calendar)}", is_flag=True)
            return
        cal_data = calendar.get("data") or {}
        self.print_nearby_sign(nick, cal_data)

        already_signed = self.is_today_signed(cal_data)
        if not already_signed:
            self.initialize.info_message(f"{nick} 今日未签到，调用领取接口…", is_flag=True)
            collect = self.collect_reward(cookies)
            if not self.ret_ok(collect):
                self.initialize.error_message(
                    f"{nick} 签到领取失败：{self.ret_msg(collect)}", is_flag=True
                )
                return
            self.print_collect_result(nick, collect.get("data") or {})

        # 推送淘金币总量（已签 / 刚领完都查一次）
        town = self.town_index(cookies)
        if self.ret_ok(town):
            town_data = town.get("data") or {}
            self.print_coin_total(nick, town_data)
            if not already_signed:
                self.print_town_index(nick, town_data)
        else:
            self.initialize.error_message(
                f"{nick} 小镇首页失败：{self.ret_msg(town)}", is_flag=True
            )

        if already_signed:
            self.initialize.info_message(f"{nick} 今日已签到，跳过领取接口", is_flag=True)


if __name__ == "__main__":
    TxSign().run()
