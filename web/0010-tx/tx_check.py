# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_check.py
# @文件介绍 :淘系 Cookie 有效性检测（getUserSimple）；失效则青龙禁用/剔除
# 青龙环境变量（前缀 TX / TX_JH / TX_LOGIN）：
#   TX_account              Cookie（淘系共用，多账号 && 或换行）
#   TX_notify               通知开关，填 1 开启
#   TX_LOGIN_client_id      青龙应用 Client ID（禁用变量需要）
#   TX_LOGIN_client_secret  青龙应用 Client Secret
#   TX_LOGIN_ql_url         青龙地址，默认 http://127.0.0.1:5700
#   也可用 QL_CLIENT_ID / QL_CLIENT_SECRET / QL_URL
# 依赖：requests
const $ = new Env('淘系Cookie检测')
cron: 1 * * * *
"""
from __future__ import annotations

import random
import sys
import time
from importlib import util
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxCheck(Base):
    def __init__(self) -> None:
        # TX_LOGIN 用于读青龙 OpenAPI 秘钥
        super().__init__(["TX", "TX_JH", "TX_LOGIN"], use_proxy=False)
        self.check_api = self.load_tool("check_cookie", "check_cookie.py")
        self.ql = self._build_qinglong()

    def load_tool(self, module_name: str, filename: str):
        path = Path(__file__).resolve().parent / "tools" / filename
        spec = util.spec_from_file_location(module_name, str(path))
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _build_qinglong(self):
        ql = self.import_set.import_qinglong()
        if ql.ready:
            return ql
        # 回退通用 QL_*
        from public.tools.qinglong import QingLongAPI

        return QingLongAPI.from_env(
            url_key="QL_URL",
            id_key="QL_CLIENT_ID",
            secret_key="QL_CLIENT_SECRET",
            default_url=ql.base_url or "http://127.0.0.1:5700",
        )

    @staticmethod
    def cookies_to_dict(account: dict) -> dict:
        raw = account.get("cookie") or account.get("Cookie") or ""
        if raw:
            result = {}
            for part in str(raw).split(";"):
                part = part.strip()
                if "=" in part:
                    key, value = part.split("=", 1)
                    result[key.strip()] = value.strip()
            return result
        if account.get("token") and len(account) == 1:
            return TxCheck.cookies_to_dict({"cookie": account["token"]})
        return {k: v for k, v in account.items() if v is not None}

    @staticmethod
    def split_accounts(value: str) -> list[str]:
        raw = (value or "").strip()
        if not raw:
            return []
        if "&&" in raw:
            return [p.strip() for p in raw.split("&&") if p.strip()]
        if "\n" in raw:
            return [p.strip() for p in raw.splitlines() if p.strip()]
        return [raw]

    @staticmethod
    def segment_id(segment: str) -> str:
        jar = TxCheck.cookies_to_dict({"cookie": segment})
        for key in ("unb", "tracknick", "lgc", "_nk_", "dnk"):
            val = str(jar.get(key) or "").strip()
            if val:
                return unquote(val)
        return ""

    def disable_or_remove_cookie(self, cookies: dict, nick: str) -> str:
        """
        失效 Cookie 处理：
        - 环境变量仅 1 个账号 → 禁用该变量
        - 多账号 → 从 value 中剔除该账号；若剔空则禁用变量
        """
        if not self.ql.ready:
            return (
                "未配置青龙 OpenAPI（TX_LOGIN_client_id/secret 或 QL_CLIENT_ID/SECRET），"
                "无法自动禁用"
            )

        env_name = self.initialize.env_key("account")
        envs = self.ql.find_envs(env_name)
        if not envs:
            return f"青龙未找到环境变量 {env_name}"

        target_id = self.check_api.account_id(cookies)
        actions: list[str] = []
        for env in envs:
            value = env.get("value") or ""
            parts = self.split_accounts(value)
            if not parts:
                self.ql.disable_env(env)
                actions.append(f"已禁用空变量 {env_name}#{env.get('id')}")
                continue

            if len(parts) == 1:
                # 单账号：整段禁用
                self.ql.disable_env(env)
                actions.append(f"已禁用 {env_name}#{env.get('id')}（{nick}）")
                continue

            kept = []
            removed = False
            for part in parts:
                sid = self.segment_id(part)
                if target_id and sid and sid == target_id:
                    removed = True
                    continue
                # 兜底：整段 Cookie 字符串相等
                if part == self._cookies_to_raw(cookies):
                    removed = True
                    continue
                kept.append(part)

            if not removed:
                actions.append(
                    f"{env_name}#{env.get('id')} 未匹配到账号 {nick}，跳过"
                )
                continue

            if not kept:
                self.ql.disable_env(env)
                actions.append(f"已剔除并禁用 {env_name}#{env.get('id')}（{nick}）")
            else:
                sep = "\n" if "\n" in value else "&&"
                new_value = sep.join(kept)
                remarks = env.get("remarks") or ""
                if "失效已剔除" not in remarks:
                    remarks = (remarks + " | 失效已剔除").strip(" |")
                self.ql.update_env(env, new_value, remarks=remarks)
                actions.append(
                    f"已从 {env_name}#{env.get('id')} 剔除失效账号 {nick}，剩余 {len(kept)} 个"
                )

        return "；".join(actions) if actions else "未执行禁用操作"

    @staticmethod
    def _cookies_to_raw(cookies: dict) -> str:
        return "; ".join(
            f"{k}={v}" for k, v in cookies.items() if v is not None and str(v) != ""
        )

    def check_one(self, account_name: str, account: dict) -> bool:
        cookies = self.cookies_to_dict(account)
        nick = self.check_api.account_label(cookies, account_name)
        if not cookies:
            self.initialize.error_message(
                f"{account_name} Cookie 为空", is_flag=True
            )
            return False

        result = self.check_api.get_user_simple(cookies)
        if result.get("ok"):
            show = result.get("nick") or nick
            uid = result.get("user_num_id")
            self.initialize.info_message(
                f"{show} Cookie 有效（userNumId={uid}）",
                is_flag=True,
            )
            return True

        self.initialize.error_message(
            f"{nick} Cookie 失效：{result.get('message')}",
            is_flag=True,
        )
        try:
            action = self.disable_or_remove_cookie(cookies, nick)
            self.initialize.error_message(action, is_flag=True)
        except Exception as exc:
            self.initialize.error_message(
                f"{nick} 青龙禁用失败：{exc}", is_flag=True
            )
        return False

    def run(self) -> None:
        task_name = "TX Cookie Check"
        notify_title = "TX Cookie Check"
        self.initialize.info_message(f"{task_name} start")
        accounts = self.initialize.load_accounts()
        if not accounts:
            env_name = self.initialize.env_key("account")
            self.initialize.error_message(
                f"未配置环境变量 {env_name}",
                is_flag=True,
            )
            self.initialize.send_notify(notify_title)
            return

        ok_n = 0
        bad_n = 0
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(
                f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}"
            )
            try:
                if self.check_one(account_name, account):
                    ok_n += 1
                else:
                    bad_n += 1
            except Exception as exc:
                bad_n += 1
                self.initialize.error_message(
                    f"{account_name} 检测异常：{exc}", is_flag=True
                )
            if index < len(accounts):
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)

        self.initialize.info_message(
            f"检测结束：有效 {ok_n}，失效 {bad_n}",
            is_flag=True,
        )
        self.initialize.info_message(f"{task_name} end")
        self.initialize.send_notify(notify_title)


if __name__ == "__main__":
    TxCheck().run()
