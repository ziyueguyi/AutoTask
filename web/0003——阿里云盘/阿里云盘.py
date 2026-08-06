# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :阿里云盘.py
# @文件介绍 :阿里云盘多账号签到并领取当日奖励
# refresh_token 获取：
#   1. 浏览器登录 https://www.aliyundrive.com/
#   2. F12 控制台执行：JSON.parse(localStorage.token).refresh_token
#   或 Application → Local Storage → token 项中复制 refresh_token
# 青龙环境变量（前缀 ALI）：
#   ALI_account  可直接填 refresh_token，或 {"refresh_token":"xxx"}；多账号用 & 或换行分隔
#   ALI_notify   通知开关，填 1 开启
# 领奖需 Windows 客户端签名头（可复用抓包，Authorization 用脚本刷新的 token）：
#   ALI_device_id / ALI_x_timestamp / ALI_x_nonce / ALI_x_signature_v2 / ALI_x_signature
#   失效时从 aDrive 客户端重新抓 sign_in_reward 请求更新上述变量
const $ = new Env('阿里云盘')
cron: 0 8 * * *
"""
import os
import random
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests


class AliyunDrive:
    def __init__(self) -> None:
        self.TOKEN_URL = "https://auth.aliyundrive.com/v2/account/token"
        self.USER_URL = "https://user.aliyundrive.com/v2/user/get"
        self.STORAGE_URL = "https://api.aliyundrive.com/v2/user/get"
        self.SIGN_URL = "https://member.aliyundrive.com/v1/activity/sign_in_list"
        self.SIGN_LIST_V2_URL = "https://member.aliyundrive.com/v2/activity/sign_in_list"
        self.REWARD_URL = "https://member.aliyundrive.com/v1/activity/sign_in_reward"
        self.PARAMS = {"_rx-s": "mobile"}
        self.APP_ID = "pJZInNHN2dZWk8qg"
        self.MAX_RETRIES = 3
        # 领奖接口需要 Windows 客户端抓包头（除 Authorization 外可复用；可用 ALI_* 覆盖）
        self.REWARD_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) aDrive/6.9.3 Chrome/112.0.5615.165 Electron/24.1.3.6 Safari/537.36"
        self.REWARD_CANARY = "client=windows,app=adrive,version=v6.9.3"
        self.REWARD_DEVICE_ID = os.getenv(
            "ALI_device_id",
            "bfb945d557201aea11eb90a69dc660bc392b6ce6f903570b2ff9fb64655b9592",
        )
        self.REWARD_TIMESTAMP = os.getenv("ALI_x_timestamp", "1785981436496")
        self.REWARD_NONCE = os.getenv("ALI_x_nonce", "4fc17dea-8ef2-4012-88f6-be75bd53ab12")
        self.REWARD_SIGNATURE_V2 = os.getenv("ALI_x_signature_v2", "12e7d7653f44f5935e61efb3f77410ac557f9f41")
        self.UA_LIST = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.163 Mobile Safari/537.36",
            "AliApp(AYSD/6.0.0) com.alicloud.databox/37029260 Channel/36176727979800@rimet_android_6.0.0 language/zh-CN /Android",
        ]
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"), )
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("ALI")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session(timeout=15)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": random.choice(self.UA_LIST),
            "x-canary": "client=Android,app=adrive,version=v6.0.0",
        })

    def auth_headers(self, access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}", "User-Agent": random.choice(self.UA_LIST)}

    def post_with_retry(self, url: str, **kwargs) -> dict:
        """带重试的 POST。"""
        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.post(url, **kwargs)
                return response.json()
            except Exception as exc:
                last_error = exc
                self.initialize.error_message(f"请求失败(第{attempt}次)：{exc}")
                if attempt < self.MAX_RETRIES:
                    delay = 2 + random.random() * 5
                    time.sleep(delay)
        raise RuntimeError(f"请求失败：{last_error}")

    def refresh_access_token(self, refresh_token: str) -> tuple[str, str] | None:
        """用 refresh_token 换取 access_token，并返回昵称。"""
        data = self.post_with_retry(self.TOKEN_URL,
                                    json={"grant_type": "refresh_token", "refresh_token": refresh_token})
        if data.get("code") or not data.get("access_token"):
            self.initialize.error_message(f"Token 刷新失败：{data.get('code') or ''} {data.get('message', data)}",
                                          is_flag=True)
            return None
        nickname = data.get("nick_name") or data.get("user_name") or "阿里云盘用户"
        return data["access_token"], nickname

    def get_user_info(self, access_token: str, fallback_name: str) -> str:
        """获取用户信息。"""
        data = self.post_with_retry(self.USER_URL, headers=self.auth_headers(access_token), json={})
        nickname = data.get("nick_name") or data.get("user_name") or fallback_name
        phone = data.get("phone") or ""
        self.initialize.info_message(f"用户：{nickname}", is_flag=True)
        if phone:
            masked = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else "***"
            self.initialize.info_message(f"手机：{masked}", is_flag=True)
        return nickname

    def get_storage_info(self, access_token: str) -> None:
        """获取存储容量信息。"""
        data = self.post_with_retry(self.STORAGE_URL, headers=self.auth_headers(access_token), json={})
        space = data.get("personal_space_info") or {}
        used_gb = round((space.get("used_size") or 0) / (1024 ** 3), 2)
        total_gb = round((space.get("total_size") or 0) / (1024 ** 3), 2)
        if total_gb > 0:
            percent = round(used_gb / total_gb * 100, 1)
            self.initialize.info_message(f"存储：{used_gb}GB / {total_gb}GB ({percent}%)", is_flag=True)
        else:
            self.initialize.info_message(f"存储：{used_gb}GB", is_flag=True)

    def reward_headers(self, access_token: str) -> dict:
        """领奖专用头：按 Windows aDrive 客户端抓包字段组装。"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": "zh-CN",
            "User-Agent": self.REWARD_UA,
            "x-device-id": self.REWARD_DEVICE_ID,
            "x-canary": self.REWARD_CANARY,
            "x-timestamp": self.REWARD_TIMESTAMP,
            "x-nonce": self.REWARD_NONCE,
            "x-signature-v2": self.REWARD_SIGNATURE_V2,
            # "x-signature": self.REWARD_SIGNATURE,
        }

    def receive_reward(self, access_token: str, day: int) -> None:
        """领取签到天数对应的奖励（signInDay 需为字符串）。"""
        response = self.session.post(
            self.REWARD_URL,
            headers=self.reward_headers(access_token),
            json={"signInDay": str(day)},
        )
        try:
            data = response.json()
        except Exception:
            self.initialize.error_message(f"奖励领取失败：HTTP {response.status_code} {response.text[:200]}", is_flag=True)
            return
        if data.get("success"):
            result = data.get("result") or {}
            notice = result.get("notice") or "，".join(str(v) for v in (result.get("name"), result.get("description")) if v)
            self.initialize.info_message(f"签到奖励：{notice or '领取成功'}", is_flag=True)
            return
        message = data.get("message") or f"HTTP {response.status_code}"
        if "已领取" in str(message):
            self.initialize.info_message(f"奖励已领取过：{message}", is_flag=True)
        else:
            self.initialize.error_message(f"奖励领取失败：{message}", is_flag=True)

    def get_sign_in_list_v2(self, access_token: str, sign_in_count: int) -> None:
        """获取 v2 签到详情。"""
        data = self.post_with_retry(self.SIGN_LIST_V2_URL, params=self.PARAMS, headers=self.auth_headers(access_token),
                                    json={})
        if not data.get("success"):
            self.initialize.error_message(f"获取签到详情失败：{data.get('message', data)}", is_flag=True)
            return
        result = data.get("result") or {}
        logs = result.get("signInLogs") or []
        signed_days = {item.get("day") for item in logs if item.get("day")}
        current_day = time.localtime().tm_mday
        calendar = "".join("✅" if day in signed_days else "⬜" for day in range(1, current_day + 1))
        self.initialize.info_message(f"本月签到：{calendar}", is_flag=True)
        infos = result.get("signInInfos") or []
        today_info = next((item for item in infos if item.get("day") == sign_in_count and item.get("signed")), None)
        for reward in (today_info or {}).get("rewards") or []:
            label = {"dailySignIn": "签到奖励", "dailyTask": "任务奖励"}.get(reward.get("type"),
                                                                             reward.get("type") or "奖励")
            detail = f"{reward.get('name') or ''} {reward.get('remind') or ''}".strip()
            if detail:
                self.initialize.info_message(f"{label}：{detail}", is_flag=True)

    def sign(self, access_token: str, nickname: str) -> None:
        """签到、领奖、拉取详情。"""
        data = self.post_with_retry(self.SIGN_URL, params=self.PARAMS, headers=self.auth_headers(access_token),
                                    json={"isReward": False})
        if not data.get("success"):
            self.initialize.error_message(f"{nickname} 签到失败：{data.get('message', data)}", is_flag=True)
            return
        day = (data.get("result") or {}).get("signInCount") or 0
        self.initialize.info_message(f"{nickname} 本月已签到 {day} 天", is_flag=True)
        if day:
            self.receive_reward(access_token, int(day))
            self.get_sign_in_list_v2(access_token, int(day))

    def run(self) -> None:
        self.initialize.info_message("签到开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(
                f"未配置账号，请在青龙面板设置环境变量 {self.env_name}（直接填 refresh_token 即可）")
            return
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个账户：{account_name}")
            refresh_token = account.get("refresh_token") or account.get("token")
            if not refresh_token:
                self.initialize.error_message(f"{account_name} 缺少 refresh_token", is_flag=True)
                continue
            try:
                token_info = self.refresh_access_token(refresh_token)
                if not token_info:
                    continue
                access_token, nickname = token_info
                nickname = self.get_user_info(access_token, nickname)
                self.get_storage_info(access_token)
                self.sign(access_token, nickname)
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True)
            if index < len(accounts):
                delay = 1 + random.random() * 4
                self.initialize.info_message(f"等待 {delay:.1f}s 后处理下一个账号...")
                time.sleep(delay)
        self.initialize.info_message("签到结束")
        self.initialize.send_notify("阿里云盘")


if __name__ == "__main__":
    AliyunDrive().run()
