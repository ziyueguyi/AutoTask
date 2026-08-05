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
        response = self.session.post(self.BASE_URL, headers={"Authorization": f"Bearer {token}"}, json={"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": "tools/call", "params": {"name": tool_name, "arguments": args or {}}, }, )
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

    def get_my_coupons(self, token: str) -> Any:
        return self.request(token, "my-coupons")

    def get_campaign_calendar(self, token: str, specified_date: str | None = None) -> Any:
        return self.request(token, "campaign-calender", {"specifiedDate": specified_date} if specified_date else {})

    def run_account(self, account_name: str, token: str) -> None:
        """单账号：查可领券 → 一键领取 → 查我的券。"""
        self.initialize.info_message(f"{account_name} 正在查询可领取的优惠券...")
        available_text = self.parse_text_content(self.get_available_coupons(token))
        if available_text:
            self.initialize.info_message(available_text)
        unreceived_count = len(re.findall(r"状态：未领取", available_text or ""))
        if unreceived_count > 0:
            self.initialize.info_message(f"{account_name} 发现 {unreceived_count} 张可领取优惠券", is_flag=True)
            self.initialize.info_message(f"{account_name} 正在一键领取优惠券...")
            bind_text = self.parse_text_content(self.auto_bind_coupons(token))
            if bind_text:
                self.initialize.info_message(bind_text)
            success_match = re.search(r"成功.*?(\d+).*?张", bind_text or "", re.S)
            if success_match:
                self.initialize.info_message(f"{account_name} 成功领取 {success_match.group(1)} 张", is_flag=True)
            coupon_names = [m.group(1).strip() for m in re.finditer(r"✅.*?\*\*(.+?)\*\*", bind_text or "") if m.group(1).strip()]
            if coupon_names:
                self.initialize.info_message(f"{account_name} 领取券：[{', '.join(coupon_names)}]", is_flag=True)
        else:
            self.initialize.info_message(f"{account_name} 暂无可领取的新优惠券", is_flag=True)
        self.initialize.info_message(f"{account_name} 正在查询我的优惠券...")
        my_text = self.parse_text_content(self.get_my_coupons(token))
        if my_text:
            self.initialize.info_message(my_text)
        total_match = re.search(r"共.*?(\d+).*?张", my_text or "")
        if total_match:
            self.initialize.info_message(f"{account_name} 当前共有 {total_match.group(1)} 张优惠券可用", is_flag=True)

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
