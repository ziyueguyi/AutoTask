# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :夸克网盘.py
# @文件介绍 :夸克网盘多账号签到领取空间容量
# 青龙环境变量（前缀 QUARK）：
#   QUARK_account  Cookie，格式 a=1;b=2 或 {"__puus":"xxx"}；多账号用 & 或换行分隔
#   QUARK_notify   通知开关，填 1 开启
#   QUARK_功能名   后续功能按此前缀扩展
const $ = new Env('夸克网盘')
cron: 35 7 * * *
"""
from importlib import util
from pathlib import Path

from curl_cffi import requests


class QuarkDrive:
    def __init__(self) -> None:
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
    def to_mb(size: int | float) -> float:
        return size / 1048576

    def check_sign(self) -> None:
        """查询今日是否已签到，未签到则执行签到。"""
        response = self.session.get(self.INFO_URL, params=self.PARAMS)
        data = response.json()
        cap_sign = (data.get("data") or {}).get("cap_sign") or {}
        if not cap_sign:
            self.initialize.error_message(f"查询签到信息失败：{data.get('message', response.text)}", is_flag=True)
            return
        if cap_sign.get("sign_daily"):
            number = self.to_mb(cap_sign.get("sign_daily_reward") or 0)
            progress = round((cap_sign.get("sign_progress") or 0) / (cap_sign.get("sign_target") or 1) * 100)
            self.initialize.info_message(f"今日已签到,获取{number}MB，进度{progress}%", is_flag=True)
            return
        self.sign()

    def sign(self) -> None:
        """执行签到。"""
        response = self.session.post(self.SIGN_URL, params=self.PARAMS, json={"sign_cyclic": True})
        data = response.json()
        if data.get("status") == 200:
            number = self.to_mb((data.get("data") or {}).get("sign_daily_reward") or 0)
            self.initialize.info_message(f"签到成功,本次签到领取{number}MB", is_flag=True)
            return
        self.initialize.error_message(f"签到失败：{data.get('message', response.text)}", is_flag=True)

    def run(self) -> None:
        self.initialize.info_message("签到开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            return
        for index, (account_name, cookies) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个账户：{account_name}")
            if cookies.get("token") and len(cookies) == 1:
                self.initialize.error_message(f"{account_name} Cookie 格式无效，请填写完整 Cookie", is_flag=True)
                continue
            try:
                self.session.cookies.clear()
                self.session.cookies.update(cookies)
                self.check_sign()
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True)
        self.initialize.info_message("签到结束")
        self.initialize.send_notify("夸克网盘")


if __name__ == "__main__":
    QuarkDrive().run()
