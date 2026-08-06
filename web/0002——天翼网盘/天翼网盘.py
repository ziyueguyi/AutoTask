# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :天翼网盘.py
# @文件介绍 :天翼云盘 Cookie 登录、每日签到抽奖、容量对比推送
# 青龙环境变量（前缀 TY）：
#   TY_account  网页 Cookie（必须含 COOKIE_LOGIN_USER）
#               Cookie 串：COOKIE_LOGIN_USER=xxx; JSESSIONID=yyy; ...
#               JSON：{"COOKIE_LOGIN_USER":"xxx","JSESSIONID":"yyy"}
#               多账号用 && 或换行分隔
#   TY_notify   通知开关，填 1 开启
# 依赖：curl_cffi
const $ = new Env('天翼网盘')
cron: 10 9 * * *
"""
import random
import re
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests


class TianyiCloud:
    WEB_URL = "https://cloud.189.cn"
    M_WEB_URL = "https://m.cloud.189.cn"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    )
    MOBILE_UA = (
        "Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 "
        "Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 "
        "clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6"
    )
    CLIENT_VERSION = "9.0.6"
    CLIENT_MODEL = "KB2000"
    COOKIE_KEYS = (
        "COOKIE_LOGIN_USER",
        "JSESSIONID",
        "apm_key",
        "apm_uid",
        "apm_ct",
        "apm_sid",
        "apm_ua",
    )
    # 签到活动抽奖任务（经典接口，每日各 1 次机会）
    LOTTERY_TASKS = (
        ("TASK_SIGNIN", "ACT_SIGNIN", "签到抽奖"),
        ("TASK_SIGNIN_PHOTOS", "ACT_SIGNIN", "相册抽奖"),
        ("TASK_2022_FLDFS_KJ", "ACT_SIGNIN", "黄金会员抽奖"),
    )

    def __init__(self) -> None:
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("TY")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.current_user = ""
        self.session = requests.Session(timeout=30)
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json;charset=UTF-8",
            "Referer": f"{self.WEB_URL}/web/main/",
        })

    def emit(self, text: str, ok: bool = True) -> None:
        prefix = f"[账号：{self.current_user}] " if self.current_user else ""
        msg = f"{prefix}{text}"
        if ok:
            self.initialize.info_message(msg, is_flag=True)
        else:
            self.initialize.error_message(msg, is_flag=True)

    @staticmethod
    def mask_phone(phone: str) -> str:
        text = str(phone or "")
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 7:
            return digits[:3] + "****" + digits[-4:]
        if "@" in text:
            name, _, domain = text.partition("@")
            return (name[:2] + "***@" + domain) if name else text
        return text or "unknown"

    @staticmethod
    def parse_cookie_string(raw: str) -> dict:
        cookies = {}
        for part in str(raw or "").split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            cookies[key.strip()] = value.strip()
        return cookies

    @classmethod
    def build_web_cookies(cls, account: dict) -> dict:
        cookies = {}
        raw = account.get("cookie") or account.get("Cookie") or ""
        if raw:
            cookies.update(cls.parse_cookie_string(str(raw)))
        for key in cls.COOKIE_KEYS:
            if account.get(key):
                cookies[key] = str(account[key]).strip()
        # 兼容 account_loader 直接拆出的键值对
        for key, value in account.items():
            if key in cls.COOKIE_KEYS or key.startswith("apm_"):
                if value and key not in cookies:
                    cookies[key] = str(value).strip()
        return {k: v for k, v in cookies.items() if v}

    def login_by_web_cookie(self, web_cookies: dict) -> dict:
        """用网页 Cookie（COOKIE_LOGIN_USER）直接访问，无需账密。"""
        if not web_cookies.get("COOKIE_LOGIN_USER"):
            raise RuntimeError("Cookie 缺少 COOKIE_LOGIN_USER")
        self.session.cookies.clear()
        self.session.cookies.update(web_cookies)
        brief = self.session.get(
            f"{self.WEB_URL}/api/portal/v2/getUserBriefInfo.action",
            impersonate="chrome131",
        ).json()
        if not brief.get("sessionKey") and brief.get("res_code") not in (0, "0", None):
            raise RuntimeError(f"Cookie 无效或已过期：{brief}")
        session_key = brief.get("sessionKey") or ""
        if not session_key:
            raise RuntimeError(f"未拿到 sessionKey，Cookie 可能失效：{brief}")
        account = brief.get("userAccount") or brief.get("account") or ""
        return {
            "sessionKey": session_key,
            "userAccount": account,
        }

    def api_get(self, url: str, session_key: str = "", params: dict | None = None) -> dict:
        query = dict(params or {})
        if session_key:
            query["sessionKey"] = session_key
        response = self.session.get(
            url,
            params=query,
            headers={"Referer": f"{self.WEB_URL}/web/main/"},
            impersonate="chrome131",
        )
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"HTTP {response.status_code} {response.text[:200]}") from exc

    def get_user_size_info(self, session_key: str = "") -> dict:
        return self.api_get(f"{self.WEB_URL}/api/portal/getUserSizeInfo.action", session_key)

    def user_sign(self, session_key: str = "") -> dict:
        return self.api_get(
            f"{self.WEB_URL}/mkt/userSign.action",
            session_key,
            {
                "rand": int(time.time() * 1000),
                "clientType": "TELEANDROID",
                "version": self.CLIENT_VERSION,
                "model": self.CLIENT_MODEL,
            },
        )

    def draw_prize(self, task_id: str, activity_id: str = "ACT_SIGNIN") -> dict:
        """签到活动抽奖（m.cloud.189.cn）。"""
        response = self.session.get(
            f"{self.M_WEB_URL}/v2/drawPrizeMarketDetails.action",
            params={
                "taskId": task_id,
                "activityId": activity_id,
                "noCache": random.random(),
            },
            headers={
                "User-Agent": self.MOBILE_UA,
                "Referer": f"{self.M_WEB_URL}/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                "Host": "m.cloud.189.cn",
                "Accept": "application/json;charset=UTF-8",
            },
            impersonate="chrome131",
        )
        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(f"抽奖 HTTP {response.status_code} {response.text[:200]}") from exc

    def run_lotteries(self) -> None:
        for index, (task_id, activity_id, title) in enumerate(self.LOTTERY_TASKS, 1):
            try:
                data = self.draw_prize(task_id, activity_id)
            except Exception as exc:
                self.emit(f"{title}（第{index}次）：请求失败 {exc}", ok=False)
                continue
            error = data.get("errorCode") or data.get("errorMsg")
            if error:
                code = str(data.get("errorCode") or "")
                if code in ("User_Not_Chance", "TimeOut"):
                    self.emit(f"{title}（第{index}次）：今日已抽过 / 无次数")
                else:
                    self.emit(f"{title}（第{index}次）：{code or error}")
                continue
            prize = (
                data.get("prizeName")
                or data.get("description")
                or data.get("prizeDesc")
                or "未知奖品"
            )
            self.emit(f"{title}（第{index}次）：获得 {prize}")
            time.sleep(0.8 + random.random())

    @staticmethod
    def bytes_to_mb(value) -> float:
        try:
            return float(value) / 1024 / 1024
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def bytes_to_gb(value) -> float:
        try:
            return float(value) / 1024 / 1024 / 1024
        except (TypeError, ValueError):
            return 0.0

    def report_capacity(self, before: dict, after: dict) -> None:
        before_cloud = ((before.get("cloudCapacityInfo") or {}).get("totalSize") or 0)
        after_cloud = ((after.get("cloudCapacityInfo") or {}).get("totalSize") or 0)
        before_family = ((before.get("familyCapacityInfo") or {}).get("totalSize") or 0)
        after_family = ((after.get("familyCapacityInfo") or {}).get("totalSize") or 0)
        self.emit(
            f"个人容量：⬆️ {self.bytes_to_mb(after_cloud - before_cloud):.2f}M / "
            f"{self.bytes_to_gb(after_cloud):.2f}G"
        )
        self.emit(
            f"家庭容量：⬆️ {self.bytes_to_mb(after_family - before_family):.2f}M / "
            f"{self.bytes_to_gb(after_family):.2f}G"
        )

    def run_account(self, account_name: str, account: dict) -> None:
        web_cookies = self.build_web_cookies(account)
        if not web_cookies.get("COOKIE_LOGIN_USER"):
            self.emit(
                f"{account_name} 缺少 COOKIE_LOGIN_USER，请从 https://cloud.189.cn Cookie 复制",
                ok=False,
            )
            return
        self.current_user = "cookie"
        started = time.time()
        self.emit("开始执行")
        self.emit("站点：https://cloud.189.cn/")
        try:
            self.emit("使用网页 Cookie 登录…")
            session = self.login_by_web_cookie(web_cookies)
            if session.get("userAccount"):
                self.current_user = self.mask_phone(session["userAccount"])
            session_key = session.get("sessionKey") or ""
            self.emit("登录成功")
            before = self.get_user_size_info(session_key)
            sign = self.user_sign(session_key)
            is_sign = sign.get("isSign")
            bonus = sign.get("netdiskBonus")
            if str(is_sign).lower() in ("true", "1"):
                self.emit(f"个人签到：今日已签到，获得 {bonus}M 空间")
            else:
                self.emit(f"个人签到：成功，获得 {bonus}M 空间")
            self.run_lotteries()
            after = self.get_user_size_info(session_key)
            self.report_capacity(before, after)
        except Exception as exc:
            self.emit(f"执行失败：{exc}", ok=False)
        finally:
            self.emit(f"执行完毕，耗时 {(time.time() - started):.2f} 秒")
            self.current_user = ""

    def run(self) -> None:
        self.initialize.info_message("天翼网盘开始")
        accounts = self.initialize.load_accounts()

        if not accounts:
            self.initialize.error_message(
                f"未配置账号。请设置 {self.env_name}=Cookie（必须含 COOKIE_LOGIN_USER）"
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
        self.initialize.info_message("天翼网盘结束")
        self.initialize.send_notify("天翼网盘 | https://cloud.189.cn/")


if __name__ == "__main__":
    TianyiCloud().run()
