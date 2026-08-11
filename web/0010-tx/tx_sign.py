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
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxSign(Base):

    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH"])
        self.app_key = "12574478"
        self.host = "https://h5api.m.taobao.com"
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

    def session_cookie_dict(self) -> dict[str, str]:
        jar: dict[str, str] = {}
        try:
            for cookie in self.session.cookies.jar:
                jar[cookie.name] = cookie.value
        except Exception:
            try:
                jar.update({k: str(v) for k, v in dict(self.session.cookies).items()})
            except Exception:
                pass
        return jar

    def apply_cookies(self, cookies: dict[str, str]) -> None:
        """清空并写入当前账号 Cookie 到 session。"""
        try:
            self.session.cookies.clear()
        except Exception:
            pass
        for name, value in cookies.items():
            if value is None or str(value) == "":
                continue
            for domain in (".taobao.com", ".tmall.com", "h5api.m.taobao.com"):
                try:
                    self.session.cookies.set(name, str(value), domain=domain)
                except Exception:
                    try:
                        self.session.cookies.set(name, str(value))
                    except Exception:
                        pass

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
        return "; ".join(
            f"{k}={v}" for k, v in self.session_cookie_dict().items() if v is not None and str(v) != ""
        )

    def query_user_taocoin(self) -> None:
        """
        拉取/刷新 _m_h5_tk（令牌过期时下发新 token）。
        Cookie 必须走 headers['cookie']，不要用 cookies=get_dict()。
        """
        url = "https://h5api.m.taobao.com/h5/mtop.taobao.pc.growth.taocoin.queryusertaocoin/1.0/"
        params = {
            "jsv": "2.5.1",
            "appKey": "12574478",
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
            "accept-language": "zh,zh-CN;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": "https://jianghu.taobao.com/coin.html",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
            "cookie": self.session_cookie_header(),
        }
        response = requests.get(url, params=params, headers=headers, timeout=20)
        new_tk = response.cookies.get("_m_h5_tk")
        new_enc = response.cookies.get("_m_h5_tk_enc")
        if new_tk:
            self.apply_cookies({
                **self.session_cookie_dict(),
                "_m_h5_tk": new_tk,
                **({"_m_h5_tk_enc": new_enc} if new_enc else {}),
            })
            self.initialize.info_message("_m_h5_tk重置成功")
        else:
            self.initialize.error_message("_m_h5_tk重置失败")

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
        self.initialize.info_message(msg, is_flag=True)

    def do_work(self, nick: str) -> None:
        calendar = self.sign_calendar()
        if not self.ret_ok(calendar):
            self.initialize.error_message(f"{nick} 签到查询失败：{self.ret_msg(calendar)}", is_flag=True)
            return
        cal_data = calendar.get("data") or {}
        self.print_nearby_sign(nick, cal_data)

        already_signed = self.is_today_signed(cal_data)
        if not already_signed:
            self.initialize.info_message(f"{nick} 今日未签到，调用领取接口…")
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
            self.initialize.info_message(f"{nick} 今日已签到，跳过领取接口")

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
                        f"{account_name} Cookie 为空",
                    is_flag=True,
                    )
                else:
                    self.apply_cookies(cookies)
                    nick = self.account_nick(account_name)
                    self.do_work(nick)
            except Exception as exc:
                self.initialize.error_message(
                    f"{account_name} 执行失败：{exc}",
                is_flag=True,
                )
            if index < len(accounts):
                delay = random.uniform(2.0, 5.0)
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message(f"{task_name} end")
        self.initialize.send_notify(notify_title)


if __name__ == "__main__":
    TxSign().run()
