# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :哈基米.py
# @文件介绍 :哈基米（gemai.huchan.cn）登录 + Cookie 复用 + 每日签到
# 账号获取：https://gemai.huchan.cn/
# 青龙环境变量（前缀 HJM）：
#   HJM_account       必填。JSON 示例：
#                     {"username":"用户名","password":"密码"}
#                     登录成功后会自动写入 cookie / user_id：
#                     {"username":"...","password":"...","cookie":"session=...","user_id":"274946"}
#                     也可直接只配 cookie：{"cookie":"session=...","user_id":"274946"}
#                     多账号用 && 或换行分隔
#   HJM_notify        通知开关，填 1 开启
#   HJM_client_id     可选。青龙应用 Client ID（与 secret 同时配置才回写 Cookie）
#   HJM_client_secret 可选。青龙应用 Client Secret
#   HJM_ql_url        可选。青龙地址，默认 http://127.0.0.1:5700
#                     也可用通用 QL_CLIENT_ID / QL_CLIENT_SECRET / QL_URL
const $ = new Env('哈基米签到')
cron: 15 8 * * *
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from importlib import util
from pathlib import Path

import requests

# 本地硬编码（有内容则优先于 HJM_account；上青龙前请清空）
HARDCODE_ACCOUNTS: list[dict] = [
    # {"username": "会做饭的菜鸡", "password": "密码1"},
    # {"username": "紫月孤忆", "password": "密码2"},
]


class HaJiMi:
    SITE = "https://gemai.huchan.cn"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
    )

    def __init__(self) -> None:
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location(
            "ImportSet", str(public_path / "ImportSet.py")
        )
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("HJM")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.session = requests.Session()
        self.user_id = ""
        self.username = ""
        self.ql = self._build_qinglong()

    def emit(self, text: str, ok: bool = True) -> None:
        if ok:
            self.initialize.info_message(text, is_flag=True)
        else:
            self.initialize.error_message(text, is_flag=True)

    def _build_qinglong(self):
        """优先 HJM_*，回退通用 QL_*。"""
        ql = self.import_set.import_qinglong(session=None)
        if ql.ready:
            return ql
        # 通用青龙应用密钥
        base = (
            self.initialize.get_env("ql_url")
            or os.getenv("QL_URL")
            or "http://127.0.0.1:5700"
        )
        client_id = self.initialize.get_env("client_id") or os.getenv("QL_CLIENT_ID") or ""
        client_secret = (
            self.initialize.get_env("client_secret")
            or os.getenv("QL_CLIENT_SECRET")
            or ""
        )
        ql_path = Path(__file__).resolve().parent.parent.parent / "public" / "tools" / "qinglong.py"
        ql_spc = util.spec_from_file_location("qinglong", str(ql_path))
        ql_mod = util.module_from_spec(ql_spc)
        ql_spc.loader.exec_module(ql_mod)
        return ql_mod.QingLongAPI(
            base_url=base,
            client_id=client_id.strip(),
            client_secret=client_secret.strip(),
        )

    @staticmethod
    def resolve_account(account: dict) -> tuple[str, str, str, str]:
        username = str(
            account.get("username")
            or account.get("user")
            or account.get("name")
            or ""
        ).strip()
        password = str(
            account.get("password") or account.get("pwd") or account.get("pass") or ""
        ).strip()
        cookie = str(
            account.get("cookie")
            or account.get("Cookie")
            or account.get("session")
            or ""
        ).strip()
        # 兼容 {"session":"裸值"} → session=裸值
        if cookie and "=" not in cookie:
            cookie = f"session={cookie}"
        user_id = str(
            account.get("user_id")
            or account.get("userId")
            or account.get("id")
            or account.get("new_api_user")
            or ""
        ).strip()
        return username, password, cookie, user_id

    def base_headers(self, *, referer: str | None = None) -> dict:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh,zh-CN;q=0.9",
            "cache-control": "no-store",
            "origin": self.SITE,
            "pragma": "no-cache",
            "referer": referer or f"{self.SITE}/",
            "user-agent": self.USER_AGENT,
        }

    @staticmethod
    def current_month() -> str:
        return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m")

    def auth_headers(self) -> dict:
        return {"new-api-user": self.user_id} if self.user_id else {}

    def request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        params: dict | None = None,
        referer: str | None = None,
        extra_headers: dict | None = None,
        empty_body: bool = False,
    ) -> dict:
        headers = self.base_headers(referer=referer)
        if body is not None:
            headers["content-type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = self.session.request(
                method,
                f"{self.SITE}{path}",
                headers=headers,
                params=params,
                json=body if body is not None else None,
                data=b"" if empty_body and body is None else None,
                timeout=30,
            )
        except Exception as exc:
            return {"success": False, "message": f"请求异常：{exc}"}
        try:
            data = response.json()
        except Exception:
            return {
                "success": False,
                "message": f"HTTP {response.status_code} {response.text[:200]}",
            }
        if not isinstance(data, dict):
            return {"success": False, "message": f"响应异常：{data!r}"}
        return data

    # ── Cookie ─────────────────────────────────────────────
    def apply_cookie(self, cookie: str, user_id: str = "") -> None:
        self.session.cookies.clear()
        self.user_id = (user_id or "").strip()
        self.username = ""
        for part in cookie.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name, value = name.strip(), value.strip()
            if not name:
                continue
            try:
                self.session.cookies.set(name, value, domain="gemai.huchan.cn")
            except Exception:
                self.session.cookies.set(name, value)

    def current_session_cookie(self) -> str:
        value = self.session.cookies.get("session") or ""
        return f"session={value}" if value else ""

    def apply_self_profile(self, data: dict) -> dict:
        """从 /api/user/self 写入 id / username。"""
        payload = data.get("data") if isinstance(data.get("data"), dict) else {}
        if not payload:
            return {}
        uid = payload.get("id") or payload.get("user_id")
        if uid is not None and str(uid).strip():
            self.user_id = str(uid).strip()
        name = str(payload.get("username") or payload.get("display_name") or "").strip()
        if name:
            self.username = name
        return payload

    def cookie_valid(self) -> dict | None:
        """GET /api/user/self 校验 Cookie；成功返回 data，失败返回 None。"""
        data = self.fetch_self()
        if data.get("success") and isinstance(data.get("data"), dict):
            return data.get("data") or {}
        msg = str(data.get("message") or data)
        # 常见失效：未登录 / unauthorized / 空消息但 success=false
        self.emit(f"Cookie 无效：{msg or 'success=false'}")
        return None

    def ensure_login(self, username: str, password: str, cookie: str, user_id: str) -> bool:
        """
        有 Cookie 先走 /api/user/self 校验；有效则跳过登录，无效再用账密登录。
        仅 Cookie、无密码时：无效则失败。
        """
        if cookie:
            self.emit("检测到已有 Cookie，正在用 /api/user/self 校验…")
            self.apply_cookie(cookie, user_id)
            profile = self.cookie_valid()
            if profile is not None:
                self.emit(
                    f"Cookie 有效，跳过登录：{self.username or username or '未知'}"
                    f"（id={self.user_id or user_id or '?'}）"
                )
                # 账号里写了用户名时，与 self.username 不一致则提示（仍继续）
                if username and self.username and username != self.username:
                    self.emit(
                        f"注意：配置用户名「{username}」与 Cookie 用户「{self.username}」不一致"
                    )
                return True
            self.emit("Cookie 已失效，准备重新登录")

        if not username or not password:
            self.emit("无有效 Cookie，且缺少 username/password，无法登录", ok=False)
            return False

        if not self.login(username, password):
            return False
        # 登录后回写青龙（未配置则跳过，仅本进程使用 Cookie）
        self.save_cookie_to_qinglong(self.username or username, password)
        return True

    def login(self, username: str, password: str) -> bool:
        """POST /api/user/login → 写入 session Cookie，并记录 new-api-user。"""
        self.session.cookies.clear()
        self.user_id = ""
        self.username = ""
        data = self.request_json(
            "POST",
            "/api/user/login?turnstile=",
            body={"username": username, "password": password},
            referer=f"{self.SITE}/sign-in?redirect=%2Fprofile",
        )
        if not data.get("success"):
            self.emit(f"登录失败：{data.get('message') or data}", ok=False)
            return False

        payload = data.get("data") or {}
        if isinstance(payload, dict):
            uid = payload.get("id") or payload.get("user_id") or payload.get("userId")
            if uid is not None and str(uid).strip():
                self.user_id = str(uid).strip()

        if not self.session.cookies.get("session"):
            token = ""
            if isinstance(payload, dict):
                token = str(
                    payload.get("token") or payload.get("access_token") or ""
                ).strip()
            if not token:
                token = str(data.get("token") or "").strip()
            if token:
                self.session.cookies.set("session", token, domain="gemai.huchan.cn")

        if not self.session.cookies.get("session"):
            self.emit("登录失败：未拿到 session Cookie", ok=False)
            return False

        if isinstance(payload, dict):
            name = str(
                payload.get("username") or payload.get("display_name") or ""
            ).strip()
            if name:
                self.username = name

        # 再拉 self，对齐 id / username（以 self 为准）
        self_info = self.fetch_self()
        if not self_info.get("success"):
            self.emit(
                f"登录成功但 /api/user/self 校验失败：{self_info.get('message') or self_info}",
                ok=False,
            )
            return False

        self.emit(
            f"登录成功：{self.username or username}"
            + (f"（id={self.user_id}）" if self.user_id else "")
        )
        return True

    # ── 青龙回写 ───────────────────────────────────────────
    def build_account_payload(self, username: str, password: str) -> dict:
        payload = {}
        # 优先用 self 返回的 username，便于与面板展示一致
        name = self.username or username
        if name:
            payload["username"] = name
        if password:
            payload["password"] = password
        cookie = self.current_session_cookie()
        if cookie:
            payload["cookie"] = cookie
        if self.user_id:
            payload["user_id"] = self.user_id
        return payload

    def merge_accounts_text(self, old_value: str, new_item: dict) -> str:
        """按 username / user_id 合并，输出换行分隔的 JSON。"""
        loader_path = (
            Path(__file__).resolve().parent.parent.parent
            / "public"
            / "tools"
            / "account_loader.py"
        )
        loader_spc = util.spec_from_file_location("account_loader", str(loader_path))
        loader = util.module_from_spec(loader_spc)
        loader_spc.loader.exec_module(loader)

        items: list[dict] = []
        for part in loader.split_multi_account(old_value or ""):
            try:
                items.append(loader.parse_cookie_item(part))
            except Exception:
                continue

        key_user = str(new_item.get("username") or "").strip()
        key_uid = str(new_item.get("user_id") or "").strip()
        replaced = False
        merged: list[dict] = []
        for item in items:
            same = False
            if key_user and str(item.get("username") or "").strip() == key_user:
                same = True
            elif key_uid and str(item.get("user_id") or item.get("id") or "").strip() == key_uid:
                same = True
            if same:
                keep = dict(item)
                keep.update({k: v for k, v in new_item.items() if v})
                merged.append(keep)
                replaced = True
            else:
                merged.append(item)
        if not replaced:
            merged.append(new_item)
        return "\n".join(json.dumps(x, ensure_ascii=False) for x in merged)

    def save_cookie_to_qinglong(self, username: str, password: str) -> None:
        cookie = self.current_session_cookie()
        if not cookie:
            return
        payload = self.build_account_payload(username, password)
        if not self.ql.ready:
            self.emit(
                "未配置青龙 client_id/secret，本次仅使用内存 Cookie，不回写面板。"
                "如需自动保存，请配置 HJM_client_id / HJM_client_secret"
                "（或 QL_CLIENT_ID / QL_CLIENT_SECRET）"
            )
            return
        try:
            self.emit(f"回写 Cookie 到青龙：{self.env_name} @ {self.ql.base_url}")
            result = self.import_set.set_env(
                "account",
                json.dumps(payload, ensure_ascii=False),
                merge=True,
                merge_fn=lambda old, _new: self.merge_accounts_text(old, payload),
                remarks="哈基米账号（自动更新 Cookie）",
                dedupe=True,
            )
            action_map = {
                "created": "已新建",
                "updated": "已覆盖更新",
                "merged": "已合并更新",
            }
            label = action_map.get(result.get("action"), "已更新")
            self.emit(f"{label} {self.env_name}（{username or self.user_id or '账号'}）")
        except Exception as exc:
            self.emit(f"回写青龙失败（不影响签到）：{exc}", ok=False)

    # ── 业务接口 ───────────────────────────────────────────
    def fetch_self(self) -> dict:
        """GET /api/user/self — Cookie 有效性与用户信息（含 username）。"""
        data = self.request_json(
            "GET",
            "/api/user/self",
            referer=f"{self.SITE}/profile",
            extra_headers=self.auth_headers() or None,
        )
        if data.get("success"):
            self.apply_self_profile(data)
        return data

    def checkin_status(self, month: str | None = None) -> dict:
        return self.request_json(
            "GET",
            "/api/user/checkin",
            params={"month": month or self.current_month()},
            referer=f"{self.SITE}/profile",
            extra_headers=self.auth_headers() or None,
        )

    def checkin(self) -> dict:
        return self.request_json(
            "POST",
            "/api/user/checkin",
            referer=f"{self.SITE}/profile",
            extra_headers=self.auth_headers() or None,
            empty_body=True,
        )

    @staticmethod
    def fmt_quota(value) -> str:
        """额度展示：原始值 / 500000，保留两位小数（如 2522010 → 5.04）。"""
        if isinstance(value, dict):
            value = value.get("quota_awarded", value.get("quota"))
        try:
            n = float(value)
        except (TypeError, ValueError):
            return str(value)
        return f"{n / 500000:.2f}"

    def emit_checkin_status(self, data: dict, *, title: str = "签到信息") -> bool | None:
        if not data.get("success"):
            self.emit(f"{title}查询失败：{data.get('message') or data}", ok=False)
            return None
        payload = data.get("data") or {}
        stats = payload.get("stats") or {}
        enabled = payload.get("enabled")
        checked = stats.get("checked_in_today")
        count = stats.get("checkin_count")
        total = stats.get("total_checkins")
        total_quota = stats.get("total_quota")
        records = stats.get("records") or []

        lines = [
            f"{title}：启用={enabled}",
            f"  今日已签={checked} | 本月={count} 次 | 累计={total} 次",
            f"  本月获额={self.fmt_quota(total_quota)}",
        ]
        if records:
            recent = records[-5:] if len(records) > 5 else records
            detail = "；".join(
                f"{r.get('checkin_date')}+{self.fmt_quota(r.get('quota_awarded'))}"
                for r in recent
                if isinstance(r, dict)
            )
            if detail:
                lines.append(f"  记录：{detail}")
        self.emit("\n".join(lines))
        if checked is True or str(checked).lower() == "true":
            return True
        if checked is False or str(checked).lower() == "false":
            return False
        return None

    def summarize_user(self, data: dict) -> None:
        payload = data.get("data") if isinstance(data.get("data"), dict) else {}
        if not payload:
            return
        name = str(payload.get("username") or "").strip()
        display = str(payload.get("display_name") or "").strip()
        uid = payload.get("id")
        parts = []
        if name:
            parts.append(f"用户={name}")
        if display and display != name:
            parts.append(f"昵称={display}")
        if uid is not None:
            parts.append(f"id={uid}")
        for key, label in (
            ("quota", "额度"),
            ("gift_quota", "赠送"),
            ("total_quota", "总额"),
            ("used_quota", "已用"),
        ):
            if payload.get(key) is not None:
                parts.append(f"{label}={self.fmt_quota(payload.get(key))}")
        if parts:
            self.emit("账户：" + " | ".join(parts))

    def run_account(self, account_name: str, account: dict) -> None:
        username, password, cookie, user_id = self.resolve_account(account)
        if not cookie and (not username or not password):
            self.emit(
                f"{account_name} 请配置 cookie，或 username+password",
                ok=False,
            )
            return

        label = username or (f"id={user_id}" if user_id else account_name)
        self.emit(f"{account_name} 开始（{label}）")
        if not self.ensure_login(username, password, cookie, user_id):
            return

        month = self.current_month()
        status = self.checkin_status(month)
        already = self.emit_checkin_status(status, title=f"{month} 签到")

        if already is True:
            self.emit("今日已签到，跳过领取")
        else:
            result = self.checkin()
            msg = str(result.get("message") or result)
            if result.get("success"):
                reward = result.get("data")
                if reward is not None and reward != "":
                    self.emit(f"签到成功：{msg} | 获额={self.fmt_quota(reward)}")
                else:
                    self.emit(f"签到成功：{msg}")
                after = self.checkin_status(month)
                self.emit_checkin_status(after, title=f"{month} 签到(更新)")
            else:
                low = msg.lower()
                if any(x in msg for x in ("已签", "已经签到", "重复")) or "already" in low:
                    self.emit(f"今日已签到：{msg}")
                else:
                    self.emit(f"签到失败：{msg}", ok=False)

        # 签到后再拉一次 self，刷新额度展示
        self_info = self.fetch_self()
        if self_info.get("success"):
            self.summarize_user(self_info)
        elif self_info.get("message"):
            self.emit(f"查账户信息失败：{self_info.get('message')}", ok=False)

    def run(self) -> None:
        self.initialize.info_message("哈基米签到开始")
        self.emit(f"站点：{self.SITE}/")
        if self.ql.ready:
            self.emit(f"青龙已配置，登录后可回写 {self.env_name}")
        else:
            self.emit("青龙未配置 client_id/secret，将直接使用账号里的 Cookie（不回写面板）")

        if HARDCODE_ACCOUNTS:
            accounts = [
                (f"硬编码账户{i}", dict(item))
                for i, item in enumerate(HARDCODE_ACCOUNTS, 1)
                if isinstance(item, dict) and item
            ]
            self.emit(f"使用硬编码账号 {len(accounts)} 个（忽略 {self.env_name}）")
        else:
            accounts = self.initialize.load_accounts()
            self.emit(f"从 {self.env_name} 加载账号 {len(accounts)} 个")
        if not accounts:
            self.initialize.error_message(
                f'未配置账号。请填写 HARDCODE_ACCOUNTS，或设置 {self.env_name}='
                '{"username":"用户名","password":"密码"}（多账号换行或 &&）'
            )
            return

        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(
                f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}"
            )
            self.emit(f"—— 第 {index}/{len(accounts)} 个：{account_name}")
            try:
                self.run_account(account_name, account)
            except Exception as exc:
                self.emit(f"{account_name} 执行失败：{exc}", ok=False)
            if index < len(accounts):
                delay = 2 + random.random() * 3
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)

        self.initialize.info_message("哈基米签到结束")
        self.initialize.send_notify("哈基米签到 | https://gemai.huchan.cn/")


if __name__ == "__main__":
    HaJiMi().run()
