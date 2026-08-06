# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :夸克网盘.py
# @文件介绍 :夸克网盘多账号签到领取空间容量
# Cookie 获取：登录 https://pan.quark.cn → F12 → Application → Cookies → 复制为 a=1; b=2 字符串
# 青龙环境变量（前缀 QUARK）：
#   QUARK_account  Cookie 字符串，多账号用换行 / & / && 分隔
#   QUARK_notify   通知开关，填 1 开启
#   QUARK_功能名   后续功能按此前缀扩展
const $ = new Env('夸克网盘')
cron: 13 18 * * *
"""
import random
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests


class QuarkDrive:
    def __init__(self) -> None:
        self.ACCOUNT_URL = "https://pan.quark.cn/account/info"
        self.INFO_URL = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        self.SIGN_URL = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        self.PARAMS = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"), )
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("QUARK")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session(timeout=15)
        self.session.headers.update({"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"})

    @staticmethod
    def cookies_to_header(cookies: dict) -> str:
        """将账号字典还原为 Cookie 请求头。"""
        if cookies.get("cookie"):
            return str(cookies["cookie"])
        if cookies.get("Cookie"):
            return str(cookies["Cookie"])
        if cookies.get("token") and len(cookies) == 1:
            return str(cookies["token"])
        return "; ".join(f"{key}={value}" for key, value in cookies.items())

    @staticmethod
    def to_mb(size: int | float) -> int:
        return int((size or 0) / 1024 / 1024)

    def set_cookie(self, cookies: dict) -> None:
        cookie = self.cookies_to_header(cookies)
        self.session.headers["Cookie"] = cookie
        self.session.cookies.clear()

    def get_account_info(self) -> dict | None:
        response = self.session.get(self.ACCOUNT_URL, params={"fr": "pc", "platform": "pc"})
        data = response.json()
        return data.get("data") or None

    def get_growth_info(self) -> dict | None:
        response = self.session.get(self.INFO_URL, params=self.PARAMS)
        data = response.json()
        return data.get("data") or None

    def get_growth_sign(self) -> tuple[bool, int | str]:
        response = self.session.post(self.SIGN_URL, params=self.PARAMS, json={"sign_cyclic": True})
        data = response.json()
        if data.get("data"):
            return True, data["data"]["sign_daily_reward"]
        return False, data.get("message") or "签到失败"

    def do_sign(self, account_name: str) -> None:
        account_info = self.get_account_info()
        if not account_info:
            self.initialize.error_message(f"{account_name} 登录失败，Cookie 无效", is_flag=True)
            return
        nickname = account_info.get("nickname") or account_name
        self.initialize.info_message(f"昵称: {nickname}", is_flag=True)
        growth_info = self.get_growth_info()
        if not growth_info:
            self.initialize.error_message(f"{nickname} 获取签到信息失败", is_flag=True)
            return
        cap_sign = growth_info.get("cap_sign") or {}
        progress, target = cap_sign.get("sign_progress") or 0, cap_sign.get("sign_target") or 0
        if cap_sign.get("sign_daily"):
            reward = self.to_mb(cap_sign.get("sign_daily_reward") or 0)
            self.initialize.info_message(f"今日已签到+{reward}MB，连签进度({progress}/{target})", is_flag=True)
            return
        ok, result = self.get_growth_sign()
        if ok:
            self.initialize.info_message(f"今日签到+{self.to_mb(result)}MB，连签进度({progress + 1}/{target})", is_flag=True)
        else:
            self.initialize.error_message(f"签到失败：{result}", is_flag=True)

    def run(self) -> None:
        self.initialize.info_message("签到开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            return
        for index, (account_name, cookies) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个账户：{account_name}")
            try:
                self.set_cookie(cookies)
                self.do_sign(account_name)
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True)
            if index < len(accounts):
                delay = random.uniform(3, 8)
                self.initialize.info_message(f"随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)
        self.initialize.info_message("签到结束")
        self.initialize.send_notify("夸克网盘")


if __name__ == "__main__":
    QuarkDrive().run()
