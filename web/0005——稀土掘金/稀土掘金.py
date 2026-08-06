# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :稀土掘金.py
# @文件介绍 :稀土掘金每日签到 / 免费抽奖（对齐 juejin-helper checkin 成长任务）
# Cookie 获取：浏览器登录 https://juejin.cn → F12 → Application → Cookies → 复制整段
# 签到/抽奖现需 a_bogus：在签到页 Network 抓 check_in / lottery 请求 Query，写入账号
# 青龙环境变量（前缀 JJ）：
#   JJ_account  Cookie 串，或 JSON：
#               {"cookie":"...","msToken":"...","a_bogus":"...","csrf":"..."}
#               多账号用 && 或换行分隔（Cookie 内含 & 勿用单 &）
#   JJ_notify   通知开关，填 1 开启
# 依赖：curl_cffi
const $ = new Env('稀土掘金')
cron: 22 6 * * *
"""
import json
import random
import re
import time
import urllib.parse
from importlib import util
from pathlib import Path

from curl_cffi import requests


class JuejinHelper:
    API = "https://api.juejin.cn"
    SITE = "https://juejin.cn"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    )
    META_KEYS = frozenset({
        "cookie", "Cookie", "token", "msToken", "mstoken", "a_bogus", "aBogus",
        "params", "draw_params", "aid", "uuid",
        "csrf", "csrf_token", "x-secsdk-csrf-token", "secsdk_csrf_token",
    })

    def __init__(self) -> None:
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("JJ")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session(timeout=20)
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": self.SITE,
            "Referer": f"{self.SITE}/",
            "Content-Type": "application/json",
            "x-secsdk-csrf-token": "DOWNGRADE",
        })
        self.current_user = ""
        self.aid = "2608"
        self.uuid = ""
        self.extra_params: dict = {}
        self.csrf_token = ""

    def emit(self, text: str, ok: bool = True) -> None:
        prefix = f"[账号：{self.current_user}] " if self.current_user else ""
        msg = f"{prefix}{text}"
        if ok:
            self.initialize.info_message(msg, is_flag=True)
        else:
            self.initialize.error_message(msg, is_flag=True)

    @classmethod
    def cookies_to_header(cls, account: dict) -> str:
        raw = account.get("cookie") or account.get("Cookie") or ""
        if raw:
            return str(raw).strip()
        if account.get("token") and len(account) == 1:
            token = str(account["token"]).strip()
            return f"sessionid={token}; sid_tt={token}; sessionid_ss={token}"
        cookie_items = [
            (k, v) for k, v in account.items()
            if v is not None and str(v) != "" and k not in cls.META_KEYS
        ]
        if account.get("sessionid") and len(cookie_items) <= 3:
            token = str(account["sessionid"]).strip()
            return f"sessionid={token}; sid_tt={token}; sessionid_ss={token}"
        return "; ".join(f"{k}={v}" for k, v in cookie_items)

    @classmethod
    def parse_cookie_tokens(cls, cookie: str) -> tuple[str, str]:
        """从 __tea_cookie_tokens_{aid} 解析 aid / uuid。"""
        aid, uuid = "2608", ""
        for part in cookie.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key, value = key.strip(), value.strip()
            matched = re.match(r"^__tea_cookie_tokens_(\d+)$", key)
            if not matched:
                continue
            aid = matched.group(1)
            try:
                decoded = urllib.parse.unquote(urllib.parse.unquote(value))
                payload = json.loads(decoded)
                uuid = str(payload.get("user_unique_id") or payload.get("web_id") or "")
            except Exception:
                uuid = ""
            break
        return aid, uuid

    def load_sign_params(self, account: dict) -> None:
        """可选：浏览器抓到的 msToken / a_bogus / CSRF（签到、抽奖风控需要）。"""
        extra = {}
        for key in ("params", "draw_params"):
            raw = account.get(key)
            if isinstance(raw, dict):
                extra.update({str(k): str(v) for k, v in raw.items() if v})
            elif isinstance(raw, str) and raw.strip().startswith("{"):
                try:
                    extra.update(json.loads(raw))
                except json.JSONDecodeError:
                    pass
        for key in ("msToken", "mstoken", "a_bogus", "aBogus", "aid", "uuid"):
            if account.get(key):
                mapped = {"mstoken": "msToken", "aBogus": "a_bogus"}.get(key, key)
                extra[mapped] = str(account[key]).strip()
        csrf = (
            account.get("csrf")
            or account.get("csrf_token")
            or account.get("x-secsdk-csrf-token")
            or account.get("secsdk_csrf_token")
            or extra.get("csrf")
            or ""
        )
        self.csrf_token = str(csrf).strip()
        if self.csrf_token:
            self.session.headers["x-secsdk-csrf-token"] = self.csrf_token
        else:
            self.session.headers["x-secsdk-csrf-token"] = "DOWNGRADE"
        if extra.get("aid"):
            self.aid = str(extra["aid"])
        if extra.get("uuid"):
            self.uuid = str(extra["uuid"])
        self.extra_params = {
            k: str(v) for k, v in extra.items()
            if k in ("msToken", "a_bogus") and v
        }

    def set_cookie(self, account: dict) -> str:
        cookie = self.cookies_to_header(account)
        if not cookie:
            raise RuntimeError("Cookie 为空")
        if "sessionid=" not in cookie and "sid_tt=" not in cookie and "=" not in cookie:
            cookie = f"sessionid={cookie}; sid_tt={cookie}; sessionid_ss={cookie}"
        tea_aid, tea_uuid = self.parse_cookie_tokens(cookie)
        self.aid = tea_aid or self.aid
        self.uuid = tea_uuid or self.uuid
        self.load_sign_params(account)
        self.session.headers["Cookie"] = cookie
        self.session.cookies.clear()
        return cookie

    def api_params(self, signed: bool = False) -> dict:
        params = {"aid": self.aid, "spider": "0"}
        if self.uuid:
            params["uuid"] = self.uuid
        if signed:
            params.update(self.extra_params)
        return params

    def request_data(self, method: str, path: str, body: dict | None = None, signed: bool = False):
        use_json = body is not None
        response = self.session.request(
            method,
            f"{self.API}{path}",
            params=self.api_params(signed=signed),
            json=body if use_json else None,
            data="{}" if method.upper() == "POST" and not use_json else None,
            impersonate="chrome131",
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError(
                "接口返回空（通常缺少/失效 a_bogus）。请到签到页抓取 check_in 的 "
                "msToken、a_bogus 写入 JJ_account JSON"
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"HTTP {response.status_code} {text[:200]}") from exc
        err_no = payload.get("err_no")
        # 15001：今日已签到，当作成功业务态交给上层
        if err_no in (15001, "15001"):
            return {"_already": True, "err_no": 15001, "err_msg": payload.get("err_msg")}
        if err_no not in (0, "0", None):
            raise RuntimeError(payload.get("err_msg") or f"err_no={err_no}")
        return payload.get("data")

    def login(self) -> dict:
        user = self.request_data("GET", "/user_api/v1/user/get")
        if not isinstance(user, dict) or not user.get("user_id"):
            raise RuntimeError("登录失败，请更新 Cookie")
        return user

    def get_today_status(self) -> bool:
        return bool(self.request_data("GET", "/growth_api/v1/get_today_status"))

    def check_in(self) -> dict:
        data = self.request_data("POST", "/growth_api/v1/check_in", body={}, signed=True)
        return data if isinstance(data, dict) else {}

    def get_counts(self) -> dict:
        data = self.request_data("GET", "/growth_api/v1/get_counts")
        return data if isinstance(data, dict) else {}

    def get_cur_point(self) -> int:
        data = self.request_data("GET", "/growth_api/v1/get_cur_point")
        try:
            return int(data or 0)
        except (TypeError, ValueError):
            return 0

    def get_lottery_config(self) -> dict:
        data = self.request_data("GET", "/growth_api/v1/lottery_config/get", signed=True)
        return data if isinstance(data, dict) else {}

    def draw_lottery(self) -> dict:
        data = self.request_data("POST", "/growth_api/v1/lottery/draw", body={}, signed=True)
        return data if isinstance(data, dict) else {}

    def get_my_lucky(self) -> dict:
        data = self.request_data("POST", "/growth_api/v1/lottery_lucky/my_lucky", body={}, signed=True)
        return data if isinstance(data, dict) else {}

    def run_growth(self) -> dict:
        """签到 + 统计（对齐 GrowthTask）。"""
        result = {
            "today_status": 0,
            "incr_point": 0,
            "sum_point": 0,
            "cont_count": 0,
            "sum_count": 0,
        }
        already = self.get_today_status()
        if already:
            result["today_status"] = 2
            self.emit("今日已签到")
        else:
            try:
                check = self.check_in()
                if check.get("_already") or check.get("err_no") in (15001, "15001"):
                    result["today_status"] = 2
                    self.emit("今日已签到")
                else:
                    result["today_status"] = 1
                    result["incr_point"] = int(check.get("incr_point") or 0)
                    result["sum_point"] = int(check.get("sum_point") or 0)
                    self.emit(f"签到成功，+{result['incr_point']} 矿石")
            except Exception as exc:
                result["today_status"] = 0
                self.emit(f"签到失败：{exc}", ok=False)
        counts = self.get_counts()
        result["cont_count"] = int(counts.get("cont_count") or 0)
        result["sum_count"] = int(counts.get("sum_count") or 0)
        result["sum_point"] = self.get_cur_point() or result["sum_point"]
        self.emit(f"连续签到 {result['cont_count']} 天，累计 {result['sum_count']} 天")
        self.emit(f"当前矿石 {result['sum_point']}")
        if self.extra_params.get("a_bogus"):
            self.emit("已携带 a_bogus 签名参数")
        else:
            self.emit("未配置 a_bogus，签到/抽奖可能被风控拦截", ok=False)
        return result

    def run_lottery(self) -> dict:
        """免费抽奖（对齐 LotteriesTask，只抽 free_count）。"""
        empty = {
            "free_count": 0,
            "lottery_count": 0,
            "history": {},
            "lottery_pool": {},
            "lucky_value": 0,
            "point_cost": 200,
        }
        try:
            config = self.get_lottery_config()
        except Exception as exc:
            self.emit(f"抽奖配置获取失败：{exc}", ok=False)
            return empty
        lottery_pool = {str(item.get("lottery_id")): item for item in (config.get("lottery") or [])}
        free_count = int(config.get("free_count") or 0)
        point_cost = int(config.get("point_cost") or 0)
        history: dict[str, int] = {}
        drawn = 0
        lucky_value = 0
        self.emit(f"免费抽奖次数 {free_count}，单次消耗 {point_cost} 矿石")
        while free_count > 0:
            try:
                data = self.draw_lottery()
            except Exception as exc:
                self.emit(f"抽奖失败：{exc}", ok=False)
                break
            lottery_id = str(data.get("lottery_id") or "")
            name = data.get("lottery_name") or (
                (lottery_pool.get(lottery_id) or {}).get("lottery_name") if lottery_id else "未知奖品"
            )
            history[lottery_id or name] = history.get(lottery_id or name, 0) + 1
            lucky_value = int(data.get("total_lucky_value") or lucky_value)
            drawn += 1
            free_count -= 1
            self.emit(f"抽奖获得：{name}")
            time.sleep(0.3 + random.random() * 0.7)
        return {
            "free_count": int(config.get("free_count") or 0),
            "lottery_count": drawn,
            "history": history,
            "lottery_pool": lottery_pool,
            "lucky_value": lucky_value,
            "point_cost": point_cost or 200,
        }

    def run_lucky(self) -> int:
        """读取幸运值（沾喜气已停用，仅查询）。"""
        try:
            data = self.get_my_lucky()
            value = int(data.get("total_value") or 0)
            self.emit(f"当前幸运值 {value}/6000")
            return value
        except Exception as exc:
            self.emit(f"幸运值查询跳过：{exc}", ok=False)
            return 0

    @staticmethod
    def predict_lucky_ratio(sum_point: int, point_cost: int, lucky_value: int) -> float:
        """对齐 juejin-helper 的粗略 All-in 幸运值预测。"""
        if point_cost <= 0 or sum_point <= 0:
            return 0.0
        total_draws = sum_point / point_cost
        supply = 0
        for _ in range(int(total_draws * 0.65)):
            supply += random.randint(1, 100)
        estimated = ((sum_point + supply) / point_cost) * 10 + lucky_value
        return estimated / 6000

    def run_account(self, account_name: str, account: dict) -> None:
        self.current_user = account_name
        self.extra_params = {}
        started = time.time()
        self.emit("开始执行")
        self.emit(f"站点：{self.SITE}/")
        try:
            self.set_cookie(account)
            user = self.login()
            self.current_user = user.get("user_name") or account_name
            self.emit(f"登录成功：{self.current_user}")
            growth = self.run_growth()
            lottery = self.run_lottery()
            try:
                growth["sum_point"] = self.get_cur_point()
                self.emit(f"结束后矿石 {growth['sum_point']}")
            except Exception as exc:
                self.emit(f"矿石查询失败：{exc}", ok=False)
            lucky = int(lottery.get("lucky_value") or 0)
            if lucky:
                self.emit(f"当前幸运值 {lucky}/6000")
            else:
                lucky = self.run_lucky()
            ratio = self.predict_lucky_ratio(
                growth["sum_point"],
                int(lottery.get("point_cost") or 200),
                int(lucky or 0),
            )
            self.emit(f"预测 All-in 幸运值比率 {(ratio * 100):.2f}%")
            if lottery.get("history"):
                pool = lottery.get("lottery_pool") or {}
                for lid, count in lottery["history"].items():
                    name = (pool.get(str(lid)) or {}).get("lottery_name") or lid
                    self.emit(f"抽奖统计：{name} × {count}")
        except Exception as exc:
            self.emit(f"执行失败：{exc}", ok=False)
        finally:
            self.emit(f"执行完毕，耗时 {(time.time() - started):.2f} 秒")
            self.current_user = ""

    def run(self) -> None:
        self.initialize.info_message("稀土掘金开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(
                f"未配置账号。请设置 {self.env_name}=Cookie（含 sessionid）"
            )
            return
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}")
            try:
                self.run_account(account_name, account)
            except Exception as exc:
                self.emit(f"{account_name} 执行失败：{exc}", ok=False)
            if index < len(accounts):
                delay = 2 + random.random() * 3
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message("稀土掘金结束")
        self.initialize.send_notify("稀土掘金 | https://juejin.cn/")


if __name__ == "__main__":
    JuejinHelper().run()
