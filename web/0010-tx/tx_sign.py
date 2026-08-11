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
from importlib import util
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxSign(Base):

    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH"])
        self.app_key = "12574478"
        self.host = "https://h5api.m.taobao.com"
        self.h5_token = self.load_tool("h5_token", "h5_token.py")
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": "https://huodong.taobao.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        })

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
            return TxSign.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    def session_cookie_dict(self) -> dict[str, str]:
        return self.h5_token.session_cookie_dict(self.session)

    def apply_cookies(self, cookies: dict[str, str]) -> None:
        """清空并写入当前账号 Cookie 到 session。"""
        self.h5_token.apply_cookies(self.session, cookies)

    def account_nick(self, fallback: str = "") -> str:
        jar = self.session_cookie_dict()
        for key in ("tracknick", "lgc", "_nk_", "dnk", "unb"):
            val = (jar.get(key) or "").strip()
            if val:
                return unquote(val)
        return fallback

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

    def mtop_sign_params(self, data: str, flag=True) -> tuple[str, str]:
        token = str(self.session_cookie_dict().get("_m_h5_tk", "")).split("_", 1)[0]
        if not token and flag:
            self.query_user_taocoin()
            return self.mtop_sign_params(data, flag=False)
        elif not token and not flag:
            raise KeyError("_m_h5_tk为空，获取失败")
        t = str(int(time.time() * 1000))
        sign = hashlib.md5(f"{token}&{t}&{self.app_key}&{data}".encode()).hexdigest()
        return t, sign

    def mtop_get(self, api: str, data: str, extra_params: dict | None = None, flag=True) -> dict:
        t, sign = self.mtop_sign_params(data)
        params = {
            "jsv": "2.5.1",
            "appKey": self.app_key,
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
        url = f"{self.host}/h5/{api}/1.0/"
        response = self.session.get(url, params=params)
        time.sleep(random.uniform(1.0, 5.0))
        if '令牌过期' in response.text and flag:
            self.initialize.error_message(f'原因：令牌失效，正在重置')
            self.session.cookies.update({"_m_h5_tk": ''})
            return self.mtop_get(api, response.text, extra_params, flag=False)
        else:
            return self.parse_jsonp(response.text)

    def mtop_post(self, api: str, data: str, extra_params: dict | None = None, extra_headers: dict | None = None, ):
        t, sign = self.mtop_sign_params(data)
        params = {
            "jsv": "2.5.1",
            "appKey": self.app_key,
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
        url = f"{self.host}/h5/{api}/1.0/"
        response = self.session.post(url, params=params, data={"data": data}, headers=headers, )
        time.sleep(random.uniform(1.0, 5.0))
        text = (response.text or "").strip()
        try:
            return self.parse_jsonp(text)
        except Exception as e:
            self.initialize.error_message(str(e))
            return json.loads(text)

    def sign_calendar(self) -> dict:
        return self.mtop_get(
            "mtop.coingame.sign.calendar.pure.pc",
            '{"bizCode":"taoCoin","subBizCode":"coinTown"}',
            {
                "valueType": "original",
                "jsonpIncPrefix": "tbbe",
                "type": "originaljsonp",
                "callback": "mtopjsonptbbe1",
            },
        )

    def collect_reward(self) -> dict:
        return self.mtop_post(
            "mtop.coingame.collect.reward.pc",
            '{"bizCode":"taoCoin","subBizCode":"coinTown","page":"pc"}',
        )

    def town_index(self) -> dict:
        api = "mtop.coingame.town.index.get.pc"
        data = '{"bizCode":"taoCoin","subBizCode":"coinTown"}'
        extra_params = {
            "valueType": "original",
            "jsonpIncPrefix": "tbbe",
            "type": "originaljsonp",
            "callback": "mtopjsonptbbe10",
        }
        return self.mtop_get(api, data, extra_params, )

    def session_cookie_header(self) -> str:
        """拼成 Cookie 请求头（淘宝 mtop 用 header 比 cookies= 更稳）。"""
        return self.h5_token.session_cookie_header(self.session)

    def query_user_taocoin(self) -> None:
        """拉取/刷新 _m_h5_tk（令牌过期时下发新 token）。"""
        self.h5_token.query_user_taocoin(
            self.session,
            on_ok=self.initialize.info_message,
            on_err=self.initialize.error_message,
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
            (sign.get("signCard") or {}).get("signRewardTomorrow")) or "-"
        msg = f"{display_nick} 余额 {coin}（约 {saving} 元）| 今日{signed} | {progress} | 明日可得 {tomorrow}"
        self.initialize.info_message(msg, is_flag=True, )

    def do_work(self, nick: str) -> None:
        calendar = self.sign_calendar()
        if not self.ret_ok(calendar):
            self.initialize.error_message(f"{nick} 签到查询失败：{self.ret_msg(calendar)}", is_flag=True)
            return
        cal_data = calendar.get("data") or {}
        self.print_nearby_sign(nick, cal_data)

        already_signed = self.is_today_signed(cal_data)
        if not already_signed:
            self.initialize.info_message(f"{nick} 今日未签到，调用领取接口…", is_flag=True)
            collect = self.collect_reward()
            if not self.ret_ok(collect):
                self.initialize.error_message(f"{nick} 签到领取失败：{self.ret_msg(collect)}", is_flag=True)
                return
            self.print_collect_result(nick, collect.get("data") or {})

        # 推送淘金币总量（已签 / 刚领完都查一次）
        town = self.town_index()
        if self.ret_ok(town):
            town_data = town.get("data") or {}
            self.print_coin_total(nick, town_data)
            if not already_signed:
                self.print_town_index(nick, town_data)
        else:
            self.initialize.error_message(f"{nick} 小镇首页失败：{self.ret_msg(town)}", is_flag=True)

        if already_signed:
            self.initialize.info_message(f"{nick} 今日已签到，跳过领取接口", is_flag=True)

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
                    self.apply_cookies(cookies)
                    nick = self.account_nick(account_name)
                    self.do_work(nick)
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


if __name__ == "__main__":
    TxSign().run()
