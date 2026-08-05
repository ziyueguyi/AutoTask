# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :阿里云盘.py
# @文件介绍 :阿里云盘多账号签到并领取当日奖励
# 青龙环境变量（前缀 ALI）：
#   ALI_account  账号，格式 {"refresh_token":"xxx"}，多账号用 & 或换行分隔
#   ALI_notify   通知开关，填 1 开启
#   ALI_功能名   后续功能按此前缀扩展
const $ = new Env('阿里云盘')
cron: 25 7 1 1 1
"""
from importlib import util
from pathlib import Path

from curl_cffi import requests


class AliyunDrive:
    def __init__(self) -> None:
        self.TOKEN_URL = "https://auth.aliyundrive.com/v2/account/token"
        self.SIGN_URL = "https://member.aliyundrive.com/v1/activity/sign_in_list"
        self.REWARD_URL = "https://member.aliyundrive.com/v1/activity/sign_in_reward"
        self.APP_ID = "pJZInNHN2dZWk8qg"
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
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/20D5024e iOS16.3 (iPhone15,2;zh-Hans-CN) App/4.1.3 AliApp(yunpan/4.1.3) com.alicloud.smartdrive/28278449 Channel/201200 AliApp(AYSD/4.1.3) com.alicloud.smartdrive/4.1.3 Version/16.3 Language/zh-Hans-CN /iOS Mobile/iPhone15,2 language/zh-Hans-CN",
        })

    def refresh_access_token(self, refresh_token: str) -> tuple[str, str] | None:
        """使用 refresh_token 获取访问令牌和账号昵称。"""
        response = self.session.post(
            self.TOKEN_URL,
            json={"grant_type": "refresh_token", "app_id": self.APP_ID, "refresh_token": refresh_token, },
        )
        data = response.json()
        if response.status_code >= 400 or not data.get("access_token"):
            code = data.get("code", response.status_code)
            message = data.get("message", response.text)
            self.initialize.error_message(f"Token 刷新失败：{code}，{message}", is_flag=True, )
            return None

        nickname = data.get("nick_name") or data.get("user_name") or "阿里云盘用户"
        return data["access_token"], nickname

    def receive_reward(self, access_token: str, day: int) -> None:
        """领取签到天数对应的奖励。"""
        response = self.session.post(
            self.REWARD_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"signInDay": day},
        )
        data = response.json()
        if not data.get("success"):
            self.initialize.error_message(f"奖励领取失败：{data.get('message', response.text)}", is_flag=True, )
            return

        result = data.get("result") or {}
        details = "，".join(
            str(value)
            for value in (result.get("name"), result.get("description"), result.get("notice"),)
            if value
        )
        self.initialize.info_message(
            f"签到奖励：{details or '领取成功'}",
            is_flag=True,
        )

    def sign(self, access_token: str, nickname: str) -> None:
        """签到并领取当天奖励。"""
        response = self.session.post(
            self.SIGN_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"isReward": False},
        )
        data = response.json()
        if not data.get("success"):
            self.initialize.error_message(f"{nickname} 签到失败：{data.get('message', response.text)}", is_flag=True, )
            return

        result = data.get("result") or {}
        day = result.get("signInCount")
        self.initialize.info_message(f"{nickname} 已连续签到 {day} 天", is_flag=True, )
        if day:
            self.receive_reward(access_token, int(day))

    def run(self) -> None:
        self.initialize.info_message("签到开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            return

        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个账户：{account_name}")
            refresh_token = account.get("refresh_token")
            if not refresh_token:
                self.initialize.error_message(f"{account_name} 缺少 refresh_token", is_flag=True, )
                continue
            try:
                token_info = self.refresh_access_token(refresh_token)
                if token_info:
                    self.sign(*token_info)
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True, )

        self.initialize.info_message("签到结束")
        self.initialize.send_notify("阿里云盘")


if __name__ == "__main__":
    AliyunDrive().run()
