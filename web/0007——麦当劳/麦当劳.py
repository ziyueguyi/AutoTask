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
        data = response.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(data["error"].get("message") or "请求失败")
        if isinstance(data, dict) and "result" in data:
            return data["result"]
        return data

    @staticmethod
    def parse_text_content(tool_result: Any) -> str:
        """解析 MCP 返回的文本内容。"""
        if not isinstance(tool_result, dict):
            return ""
        for item in tool_result.get("content") or []:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text") or ""
        return ""

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
            use_content = account_info.get('structuredContent', {}).get("data")
            self.initialize.info_message(f"#####累计积分：{use_content.get('accumulativePoint')}", is_flag=True)
            self.initialize.info_message(f"#####可用积分：{use_content.get('availablePoint')}", is_flag=True)
            self.initialize.info_message(f"#####冻结积分：{use_content.get('frozenPoint')}", is_flag=True)
            self.initialize.info_message(f"本月将过期积分：{use_content.get('currentMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"下月将过期积分：{use_content.get('nextMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"上月已过期积分：{use_content.get('lastMouthExpirePoint')}", is_flag=True)
            self.initialize.info_message(f"###已过期积分：{use_content.get('expiredPoint')}", is_flag=True)
            self.initialize.info_message(f"###已使用积分：{use_content.get('usedPoint')}", is_flag=True)
        coupons_list = self.get_available_coupons(token)
        self.initialize.info_message("【优惠券信息】", is_flag=True)
        unreceived_count = 0
        if not coupons_list.get("isError"):
            for coupon in coupons_list.get('structuredContent', {}).get("data", []):
                msg = f"券名：{coupon.get('couponName')}，状态：{coupon.get('label')}，图片：{coupon.get('couponImage')}"
                self.initialize.info_message(msg, is_flag=True)
                unreceived_count += 1 if coupon.get('label') not in ['已领取', '已领完'] else 0
        if unreceived_count:
            self.initialize.info_message(f"{account_name} 发现 {unreceived_count} 张可领取优惠券", is_flag=True)
            self.initialize.info_message(f"{account_name} 正在一键领取优惠券...")
            bind_coupons = self.auto_bind_coupons(token)
            if not bind_coupons.get('isError'):
                if bind_coupons.get("structuredContent", {}).get('success'):
                    self.initialize.info_message(bind_coupons)
                elif bind_coupons.get("structuredContent", {}).get('code') == 499:
                    self.initialize.error_message(bind_coupons.get("structuredContent", {}).get('message'))
                else:
                    self.initialize.error_message(bind_coupons)
            get_coupons = bind_coupons.get('structuredContent', {}).get('data') or []
            if get_coupons:
                self.initialize.info_message(f"{account_name} 成功领取 {len(get_coupons)} 张", is_flag=True)
            # if coupon_names:
            #     self.initialize.info_message(f"{account_name} 领取券：[{', '.join(coupon_names)}]", is_flag=True)
        else:
            self.initialize.info_message(f"{account_name} 暂无可领取的新优惠券")
        self.initialize.info_message(f"{account_name} 正在查询我的优惠券...")
        available_coupons = self.get_my_coupons(token)
        if not available_coupons.get('isError'):
            self.initialize.info_message("【我的优惠券】", is_flag=True)
            available_coupons_list = available_coupons.get('structuredContent', {}).get("data", []).get("coupons")
            for coupon in available_coupons_list:
                msg = f"券名：{coupon.get('title')}，日期限制：{coupon.get('datetimeText')}，用券价格：{coupon.get('discountInfo', {}).get('discountValue')}"
                self.initialize.info_message(msg, is_flag=True)
            msg = f"账户：{account_name}当前共有可用张优惠券：{len(available_coupons_list)}张"
            self.initialize.info_message(msg, is_flag=True)

    def run(self) -> None:
        self.initialize.info_message("麦当劳任务开始")
        # accounts = self.initialize.load_accounts()
        accounts = [('1', {'token': '2CfyvJCu5q3XmdHw0seNS9BjF4k1hxKy'})]
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
