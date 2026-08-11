# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :天机爻.py
# @文件介绍 :天机爻每日签到 + 每日一签查询推送
# Cookie 获取（可选）：浏览器打开 https://tianjiyao.com ，F12 → Network 复制 Cookie；遇 Cloudflare 拦截时再填
# 青龙环境变量（前缀 TJY）：
#   TJY_account  必填。JSON：{"email":"邮箱","password":"密码"}，可选 "cookie"
#                多账号用 && 或换行分隔
#   TJY_notify   通知开关，填 1 开启
const $ = new Env('天机爻签到')
cron: 10 8 * * *
"""
import random
import time
from datetime import datetime, timedelta, timezone
from importlib import util
from pathlib import Path

import requests


class TianJiYao:
    def __init__(self) -> None:
        self.API = "https://tianjiyao.com"
        self.TZ = timezone(timedelta(hours=8))
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("TJY")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session()

    def emit(self, text: str, ok: bool = True) -> None:
        if ok:
            self.initialize.info_message(text, is_flag=True)
        else:
            self.initialize.error_message(text, is_flag=True)

    def safe_call(self, label: str, fn, *args, default=None, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            self.emit(f"{label}异常（已跳过）：{exc}", ok=False)
            return default

    @staticmethod
    def resolve_account(account: dict) -> tuple[str, str, str]:
        email = str(account.get("email") or account.get("mail") or "").strip()
        password = str(account.get("password") or account.get("pwd") or "").strip()
        cookie = str(account.get("cookie") or account.get("Cookie") or "").strip()
        return email, password, cookie

    def today_parts(self) -> tuple[str, str]:
        now = datetime.now(self.TZ)
        return now.strftime("%Y-%m"), now.strftime("%Y-%m-%d")

    def request_json(
        self,
        method: str,
        path: str,
        cookie: str = "",
        token: str | None = None,
        body: dict | None = None,
        params: dict | None = None,
        referer: str | None = None,
    ) -> dict:
        headers = {
            "Origin": self.API,
            "Referer": referer or f"{self.API}/",
            "Accept": "*/*",
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36"
            ),
        }
        if cookie:
            headers["Cookie"] = cookie
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = self.session.request(
                method,
                f"{self.API}{path}",
                headers=headers,
                json=body if body is not None else None,
                params=params,
            )
        except Exception as exc:
            return {"success": False, "error": f"请求异常：{exc}"}
        try:
            return response.json()
        except Exception:
            return {
                "success": False,
                "error": f"HTTP {response.status_code} {response.text[:200]}",
            }

    def login(self, email: str, password: str, cookie: str = "") -> str | None:
        data = self.request_json(
            "POST",
            "/api/auth/login",
            cookie,
            body={"email": email, "password": password},
        )
        if not data.get("success"):
            self.emit(f"登录失败：{data.get('error') or data}", ok=False)
            return None
        token = ((data.get("session") or {}).get("access_token") or "").strip()
        if not token:
            self.emit("登录失败：未返回 access_token", ok=False)
            return None
        self.emit("登录成功")
        return token

    def check_status(self, token: str, cookie: str = "") -> dict:
        return self.request_json("GET", "/api/credits/status", cookie, token=token)

    def checkin(self, token: str, cookie: str = "") -> dict:
        return self.request_json("POST", "/api/credits/checkin", cookie, token=token, body={})

    def balance(self, token: str, cookie: str = "") -> dict:
        return self.request_json("GET", "/api/credits/balance", cookie, token=token)

    def daily_sign_list(self, token: str, cookie: str = "") -> dict:
        month, client_date = self.today_parts()
        return self.request_json(
            "GET",
            "/api/daily-sign/list",
            cookie,
            token=token,
            params={
                "month": month,
                "clientDate": client_date,
                "timezone": "Asia/Shanghai",
            },
            referer=f"{self.API}/zh/daily-sign",
        )

    def push_daily_sign(self, token: str, cookie: str = "") -> None:
        """查询每日一签并写入推送。"""
        data = self.daily_sign_list(token, cookie)
        if not data.get("success"):
            self.emit(f"每日一签查询失败：{data.get('error') or data}", ok=False)
            return
        payload = data.get("data") or {}
        records = payload.get("records") or []
        month = payload.get("month") or self.today_parts()[0]
        _, today = self.today_parts()
        self.emit(f"每日一签：https://tianjiyao.com/zh/daily-sign （{month} 共 {len(records)} 签）")
        today_item = next((item for item in records if item.get("date") == today), None)
        if not today_item and records:
            today_item = records[-1]
        if not today_item:
            self.emit("今日尚未抽签，请打开页面完成抽签后再查")
            return
        snap = today_item.get("snapshot") or {}
        poem = snap.get("poem") or []
        yi = snap.get("yi") or []
        ji = snap.get("ji") or []
        keywords = snap.get("keywords") or []
        self.emit(
            f"【今日运签 {today_item.get('date') or today}】\n"
            f"  签名：【{snap.get('name') or '未知'}】\n"
            f"  签级：{snap.get('level') or '未知'}\n"
            f"  卦名：{snap.get('hexagramName') or '未知'}\n"
            f"  主题：{snap.get('theme') or '未知'}\n"
            f"  关键词：{'、'.join(str(x) for x in keywords) if keywords else '无'}\n"
            f"  签诗：{' / '.join(str(x) for x in poem) if poem else '无'}\n"
            f"  摘要：{snap.get('summary') or '无'}\n"
            f"  宜：{'、'.join(str(x) for x in yi) if yi else '无'}\n"
            f"  忌：{'、'.join(str(x) for x in ji) if ji else '无'}"
        )

    def run_account(self, account_name: str, account: dict) -> None:
        email, password, cookie = self.resolve_account(account)
        if not email or not password:
            self.emit(f"{account_name} 缺少 email/password", ok=False)
            return
        self.emit(f"{account_name} 开始（{email}）")
        token = self.login(email, password, cookie)
        if not token:
            return

        status = self.check_status(token, cookie)
        info = status.get("data") or {}
        checked = info.get("today_checked")
        days = info.get("consecutive_days")
        next_time = info.get("next_checkin_time")
        self.emit(f"签到状态：已签={checked} | 连续={days} 天 | 下次={next_time}")

        if checked is True or str(checked).lower() == "true":
            self.emit("今日已签到，跳过")
        else:
            result = self.checkin(token, cookie)
            if result.get("success"):
                self.emit("签到成功")
            else:
                err = str(result.get("error") or result)
                if "已签到" in err or "already" in err.lower():
                    self.emit("今日已签到")
                else:
                    self.emit(f"签到失败：{err}", ok=False)

        bal = self.balance(token, cookie)
        credits = bal.get("credits") or {}
        total = credits.get("total_credits")
        available = credits.get("available_credits")
        if total is not None or available is not None:
            self.emit(f"积分：总 {total} | 可用 {available}")
        elif not bal.get("success", True):
            self.emit(f"查余额失败：{bal.get('error') or bal}", ok=False)

        self.safe_call("每日一签", self.push_daily_sign, token, cookie)

    def run(self) -> None:
        self.initialize.info_message("天机爻签到开始")
        self.emit("站点：https://tianjiyao.com/")
        accounts = self.initialize.load_accounts()
        accounts = [[1,{"email": "17630583910@163.com", "password": ".ai94264744946"}]]
        if not accounts:
            self.initialize.error_message(
                f"未配置账号。请设置 {self.env_name}="
                '{"email":"邮箱","password":"密码"}'
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
        self.initialize.info_message("天机爻签到结束")
        self.initialize.send_notify("天机爻签到 | https://tianjiyao.com/")


if __name__ == "__main__":
    TianJiYao().run()
