# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :麦当劳.py
# @文件介绍 :麦当劳 MCP 查询可领优惠券并一键领取
# Token 申请：https://open.mcd.cn/mcp/doc
# 青龙环境变量（前缀 MCD）：
#   MCD_account  账号，可直接填 token，或 {"token":"xxx"}；多账号用 & 或换行分隔
#   MCD_notify   通知开关，填 1 开启
#   MCD_功能名   后续功能按此前缀扩展
const $ = new Env('麦当劳')
cron: 30 8 * * *
"""
import re
import time
from importlib import util
from pathlib import Path
from typing import Any

from curl_cffi import requests


class McDonald:
    def __init__(self) -> None:
        self.BASE_URL = "https://mcp.mcd.cn/mcp-servers/mcd-mcp"
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"), )
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("MCD")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session(timeout=20)
        self.session.headers.update({"Content-Type": "application/json"})

    def request(self, token: str, tool_name: str, args: dict | None = None) -> Any:
        """调用麦当劳 MCP tools/call 接口。"""
        response = self.session.post(self.BASE_URL, headers={"Authorization": f"Bearer {token}"},
                                     json={"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": "tools/call",
                                           "params": {"name": tool_name, "arguments": args or {}}, }, )
        if response.status_code == 200 and 'result' in response.text:
            data = response.json().get('result', {})
            if not data.get('isError') and data.get('structuredContent', {}).get('success'):
                return data.get('structuredContent', {}).get('data', [])
            else:
                return {}
        else:
            return {}

    def get_available_coupons(self, token: str) -> Any:
        return self.request(token, "available-coupons")

    def auto_bind_coupons(self, token: str) -> Any:
        return self.request(token, "auto-bind-coupons")

    def campaign_calendar(self, token: str) -> Any:
        return self.request(token, "campaign-calendar")

    def get_my_coupons(self, token: str) -> Any:
        return self.request(token, "query-my-coupons")

    def get_my_account(self, token: str) -> Any:
        return self.request(token, "query-my-account")

    def get_campaign_calendar(self, token: str, specified_date: str | None = None) -> Any:
        return self.request(token, "campaign-calender", {"specifiedDate": specified_date} if specified_date else {})

    def run_account(self, account_name: str, token: str) -> None:
        """单账号：查可领券 → 一键领取 → 查我的券。"""
        self.initialize.info_message(f"{account_name} 正在查询可领取的优惠券...")
        account_info = self.get_my_account(token)
        self.initialize.info_message("【账户信息】", is_flag=True)
        if account_info:
            self.initialize.info_message(f"#####累计积分：{account_info.get('accumulativePoint')}", is_flag=True)
            self.initialize.info_message(f"#####可用积分：{account_info.get('availablePoint')}", is_flag=True)
            self.initialize.info_message(f"#####冻结积分：{account_info.get('frozenPoint')}", is_flag=True)
            self.initialize.info_message(f"本月将过期积分：{account_info.get('currentMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"下月将过期积分：{account_info.get('nextMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"上月已过期积分：{account_info.get('lastMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"###已过期积分：{account_info.get('expiredPoint')}", is_flag=True)
            self.initialize.info_message(f"###已使用积分：{account_info.get('usedPoint')}", is_flag=True)
        else:
            self.initialize.error_message(f"账户信息查询失败", is_flag=True)
        coupons_list = self.get_available_coupons(token)
        self.initialize.info_message("【优惠券信息】", is_flag=True)
        unreceived_count = 0
        if coupons_list:
            for coupon in coupons_list:
                msg = f"券名：{coupon.get('couponName')}，状态：{coupon.get('label')}，图片：{coupon.get('couponImage')}"
                self.initialize.info_message(msg, is_flag=True)
                unreceived_count += 1 if coupon.get('label') not in ['已领取', '已领完'] else 0
            if unreceived_count:
                self.initialize.info_message(f"{account_name} 发现 {unreceived_count} 张可领取优惠券", is_flag=True)
                self.initialize.info_message(f"{account_name} 正在一键领取优惠券...")
                bind_coupons = self.auto_bind_coupons(token)
                if bind_coupons:
                    self.initialize.info_message(bind_coupons)
                    self.initialize.info_message(f"{account_name} 成功领取 {len(bind_coupons)} 张", is_flag=True)
                else:
                    self.initialize.error_message(bind_coupons)
                # if coupon_names:
                #     self.initialize.info_message(f"{account_name} 领取券：[{', '.join(coupon_names)}]", is_flag=True)
            else:
                self.initialize.info_message(f"{account_name} 暂无可领取的新优惠券")
        else:
            self.initialize.error_message(f"优惠券查询失败", is_flag=True)
        self.initialize.info_message(f"{account_name} 正在查询我的优惠券...")
        available_coupons = self.get_my_coupons(token)
        self.initialize.info_message("【我的优惠券】", is_flag=True)
        if available_coupons:
            available_coupons_list = available_coupons.get("coupons")
            for coupon in available_coupons_list:
                msg = f"券名：{coupon.get('title')}，日期限制：{coupon.get('datetimeText')}，用券价格：{coupon.get('discountInfo', {}).get('discountValue')}"
                self.initialize.info_message(msg, is_flag=True)
            msg = f"账户：{account_name}当前共有可用张优惠券：{len(available_coupons_list)}张"
            self.initialize.info_message(msg, is_flag=True)
        else:
            self.initialize.error_message("我的优惠券获取失败", is_flag=True)
        campaign_list = self.campaign_calendar(token)
        self.initialize.info_message("【活动日历】", is_flag=True)
        if campaign_list:
            subscribed_events = campaign_list.get("subscribedEvents", [])
            for se in subscribed_events:
                coupon_info = se.get("couponInfo", {})
                sd = coupon_info.get("tradeStartDateTime")
                ed = coupon_info.get("tradeEndDateTime")
                msg = f"券名：{se.get('activityTitle')}，日期限制：{sd}_{ed}，用券价格：{coupon_info.get('discountInfo', {}).get('discountValue')}"
                self.initialize.info_message(msg, is_flag=True)
        else:
            self.initialize.error_message("活动日历查询失败", is_flag=True)

    def run(self) -> None:
        self.initialize.info_message("麦当劳任务开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            return
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个账户：{account_name}")
            token = account.get("token")
            if not token:
                self.initialize.error_message(f"{account_name} 缺少 token", is_flag=True)
                continue
            try:
                self.run_account(account_name, token)
            except Exception as exc:
                self.initialize.error_message(f"{account_name} 执行失败：{exc}", is_flag=True)
        self.initialize.info_message("麦当劳任务结束")
        self.initialize.send_notify("麦当劳")


if __name__ == "__main__":
    McDonald().run()
