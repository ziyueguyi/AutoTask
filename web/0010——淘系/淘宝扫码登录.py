# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :淘宝扫码登录.py
# @文件介绍 :淘宝 PC 扫码登录，日志打印二维码，确认后回写青龙 Cookie
# 青龙环境变量（前缀 TB_LOGIN）：
#   TB_LOGIN_client_id      青龙应用 Client ID（与 secret 同时配置才可上传）
#   TB_LOGIN_client_secret  青龙应用 Client Secret
#   TB_LOGIN_ql_url         青龙地址，默认 http://127.0.0.1:5700
#   TB_LOGIN_target         写入的环境变量名，逗号分隔；默认同步全部淘系 *_account
#   TB_LOGIN_notify         通知开关，填 1 开启
#   TB_LOGIN_timeout        等待扫码超时秒数，默认 300
# 依赖：curl_cffi、qrcode、pillow
const $ = new Env('淘宝扫码登录')
cron: 0 7 * * *
"""
from __future__ import annotations

import io
import os
import re
import sys
import time
from importlib import util
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from curl_cffi import requests


DEFAULT_TARGETS = (
    "TJB_SIGN_account,TJB_TASK_account,TJB_EXCHANGE_account,"
    "TJH_TASK_account,TJH_EXCHANGE_account"
)
IMPORTANT_COOKIE_KEYS = (
    "cookie2",
    "_tb_token_",
    "t",
    "_m_h5_tk",
    "_m_h5_tk_enc",
    "unb",
    "sgcookie",
    "tracknick",
    "lgc",
    "_nk_",
    "dnk",
    "cna",
    "isg",
    "tfstk",
    "thw",
    "wk_cookie2",
    "wk_unb",
    "env_bak",
    "mt",
    "xlly_s",
    "_samesite_flag_",
)


class TaoBaoQrLogin:
    LOGIN_HOST = "https://login.taobao.com"
    RETURN_URL = "https://www.taobao.com/"
    GENERATE_PATH = "/havanaone/loginLegacy/qrCode/generate.do"
    QUERY_PATH = "/havanaone/loginLegacy/qrCode/query.do"
    LOGIN_PAGE = "/havanaone/login/login.htm"
    POLL_INTERVAL = 10
    QR_FILENAME = "tb_login_qr.png"

    def __init__(self) -> None:
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("TB_LOGIN")
        self.initialize = self.import_set.import_initialize()

        self.ql_url = (os.getenv(self.initialize.env_key("ql_url")) or "http://127.0.0.1:5700").rstrip("/")
        self.client_id = (os.getenv(self.initialize.env_key("client_id")) or "").strip()
        self.client_secret = (os.getenv(self.initialize.env_key("client_secret")) or "").strip()
        target_raw = (os.getenv(self.initialize.env_key("target")) or DEFAULT_TARGETS).strip()
        self.targets = [x.strip() for x in target_raw.replace("，", ",").split(",") if x.strip()]
        try:
            self.timeout = int(os.getenv(self.initialize.env_key("timeout")) or "300")
        except ValueError:
            self.timeout = 300
        self.qr_path = Path(__file__).resolve().parent / self.QR_FILENAME

        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        )
        self.session = requests.Session(timeout=20, impersonate="chrome")
        proxy = (os.getenv(self.initialize.env_key("proxy")) or "").strip()
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh,zh-CN;q=0.9",
            "user-agent": self.ua,
        })
        self.login_page_url = (
            f"{self.LOGIN_HOST}{self.LOGIN_PAGE}"
            f"?bizName=taobao&f=top&redirectURL={self.RETURN_URL}"
        )
        self._csrf = ""
        self._ql_token: str | None = None

    # ---------- utils ----------

    @staticmethod
    def cookies_to_str(cookies: dict[str, str], keys: tuple[str, ...] | None = None) -> str:
        if keys:
            items = [(k, cookies[k]) for k in keys if cookies.get(k)]
        else:
            items = [(k, v) for k, v in cookies.items() if v is not None and str(v) != ""]
        return "; ".join(f"{k}={v}" for k, v in items)

    @staticmethod
    def parse_cookie_str(raw: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for part in str(raw or "").split(";"):
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    @classmethod
    def account_id(cls, cookie_str: str) -> str:
        jar = cls.parse_cookie_str(cookie_str)
        for key in ("unb", "tracknick", "lgc", "_nk_", "dnk"):
            val = (jar.get(key) or "").strip()
            if val:
                return unquote(val)
        return ""

    def session_cookie_dict(self) -> dict[str, str]:
        jar: dict[str, str] = {}
        try:
            for cookie in self.session.cookies.jar:
                jar[cookie.name] = cookie.value
        except Exception:
            jar.update({k: str(v) for k, v in dict(self.session.cookies).items()})
        return jar

    def log_qr(self, content: str) -> None:
        self.initialize.info_message("请使用淘宝 App 扫描下方二维码（或打开本地图片）")
        self.initialize.info_message(f"二维码内容: {content}")
        img_path = self.save_qr_image(content)
        self.initialize.info_message(f"本地二维码图片: {img_path}")
        text = self.render_ascii_qr(content)
        if text:
            print(text, flush=True)
        self._try_open_image(img_path)

    def save_qr_image(self, content: str) -> Path:
        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError(
                "缺少依赖 qrcode / pillow，请在青龙「依赖管理」安装：qrcode pillow"
            ) from exc

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        self.qr_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(self.qr_path)
        return self.qr_path

    @staticmethod
    def render_ascii_qr(content: str) -> str:
        try:
            import qrcode

            qr = qrcode.QRCode(border=1, box_size=1)
            qr.add_data(content)
            qr.make(fit=True)
            buf = io.StringIO()
            qr.print_ascii(out=buf, invert=True)
            return buf.getvalue().rstrip()
        except Exception:
            return ""

    @staticmethod
    def _try_open_image(path: Path) -> None:
        """本地运行时尝试打开图片；青龙容器内忽略。"""
        if os.getenv("QL_DIR") or os.getenv("QL_DATA_DIR"):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')
        except Exception:
            pass

    def cleanup_qr_image(self) -> None:
        try:
            if self.qr_path.exists():
                self.qr_path.unlink()
                self.initialize.info_message(f"已删除临时二维码: {self.qr_path}")
        except Exception as exc:
            self.initialize.error_message(f"删除临时二维码失败: {exc}")

    # ---------- login flow ----------

    def open_login_page(self) -> None:
        resp = self.session.get(self.login_page_url)
        resp.raise_for_status()
        match = re.search(r'"_csrf"\s*:\s*"([^"]+)"', resp.text)
        if not match:
            raise RuntimeError("登录页未找到 _csrf，请稍后重试")
        self._csrf = match.group(1)
        self.session.headers["referer"] = self.login_page_url

    def generate_qr(self) -> dict[str, Any]:
        params = {
            "bizEntrance": "taobao_pc",
            "bizName": "taobao",
            "hitRSA2048Gray": "true",
            "renderRefer": self.RETURN_URL,
            "_csrf": self._csrf,
            "returnUrl": self.RETURN_URL,
            "lang": "zh_CN",
            "umidToken": "",
            "umidTag": "NOT_INIT",
        }
        resp = self.session.get(f"{self.LOGIN_HOST}{self.GENERATE_PATH}", params=params)
        resp.raise_for_status()
        payload = resp.json()
        data = ((payload.get("content") or {}).get("data") or {})
        if payload.get("hasError") or not data.get("ck") or not data.get("codeContent"):
            raise RuntimeError(f"生成二维码失败: {payload}")
        return data

    def query_qr(self, t: Any, ck: str) -> dict[str, Any]:
        body = {
            "t": str(t),
            "ck": ck,
            "ua": "",
            "hitRSA2048Gray": "true",
            "bizEntrance": "taobao_pc",
            "bizName": "taobao",
            "renderRefer": self.RETURN_URL,
            "_csrf": self._csrf,
            "returnUrl": self.RETURN_URL,
            "lang": "zh_CN",
            "umidToken": "",
            "umidTag": "NOT_INIT",
            "navlanguage": "zh",
            "navUserAgent": self.ua,
            "navPlatform": "Win32",
            "isIframe": "false",
            "banThirdPartyCookie": "false",
            "documentReferer": self.RETURN_URL,
            "defaultView": "password",
        }
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "origin": self.LOGIN_HOST,
            "referer": self.login_page_url,
        }
        resp = self.session.post(
            f"{self.LOGIN_HOST}{self.QUERY_PATH}?bizEntrance=taobao_pc&bizName=taobao",
            data=body,
            headers=headers,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = ((payload.get("content") or {}).get("data") or {})
        if payload.get("hasError"):
            raise RuntimeError(f"查询扫码状态失败: {payload}")
        return data

    def wait_confirmed(self, t: Any, ck: str) -> dict[str, Any]:
        deadline = time.time() + self.timeout
        round_no = 0
        self.initialize.info_message(
            f"开始轮询扫码状态，间隔 {self.POLL_INTERVAL}s，超时 {self.timeout}s"
        )
        while time.time() < deadline:
            round_no += 1
            remain = max(0, int(deadline - time.time()))
            data = self.query_qr(t, ck)
            status = str(data.get("qrCodeStatus") or "")
            msg = data.get("titleMsg") or status or "未知状态"
            self.initialize.info_message(
                f"[{round_no}] 扫码状态: {status}（{msg}），剩余约 {remain}s"
            )
            if status == "CONFIRMED" and data.get("loginResult") == "success":
                return data
            if status == "EXPIRED":
                raise TimeoutError(f"二维码超时（EXPIRED）：{msg}")
            if status in {"CANCELED", "CANCELLED", "TIMEOUT"}:
                raise RuntimeError(f"扫码已取消或超时: {status}（{msg}）")
            time.sleep(self.POLL_INTERVAL)
        raise TimeoutError(f"等待扫码超时（{self.timeout}s）")

    def collect_cookies(self, confirmed: dict[str, Any]) -> str:
        for url in confirmed.get("asyncUrls") or []:
            try:
                self.session.get(str(url), allow_redirects=True)
            except Exception as exc:
                self.initialize.error_message(f"同步站点 Cookie 失败: {exc}")

        redirect = confirmed.get("redirectUrl") or confirmed.get("returnUrl") or self.RETURN_URL
        try:
            self.session.get(str(redirect), allow_redirects=True)
        except Exception as exc:
            self.initialize.error_message(f"访问跳转页失败: {exc}")

        # 触发 h5 token
        try:
            self.session.get(
                "https://h5api.m.taobao.com/h5/mtop.user.getusersimple/1.0/",
                params={"jsv": "2.6.1", "appKey": "12574478", "t": str(int(time.time() * 1000)), "data": "{}"},
                headers={"referer": "https://www.taobao.com/"},
                allow_redirects=True,
            )
        except Exception:
            pass

        jar = self.session_cookie_dict()
        cookie_str = self.cookies_to_str(jar, IMPORTANT_COOKIE_KEYS)
        if "cookie2" not in jar:
            raise RuntimeError("登录后未拿到 cookie2，Cookie 不完整")
        return cookie_str

    # ---------- qinglong ----------

    def can_upload(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def ql_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ql_token}",
            "Content-Type": "application/json",
        }

    def ql_get_token(self) -> str:
        if self._ql_token:
            return self._ql_token
        resp = requests.get(
            f"{self.ql_url}/open/auth/token",
            params={"client_id": self.client_id, "client_secret": self.client_secret},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"获取青龙 Token 失败: {data}")
        self._ql_token = data["data"]["token"]
        return self._ql_token

    def ql_find_env(self, name: str) -> dict[str, Any] | None:
        self.ql_get_token()
        resp = requests.get(
            f"{self.ql_url}/open/envs",
            headers=self.ql_headers(),
            params={"searchValue": name},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"获取环境变量失败: {data}")
        for env in data.get("data") or []:
            if env.get("name") == name:
                return env
        return None

    def ql_enable_env(self, env: dict[str, Any]) -> None:
        if int(env.get("status") or 0) == 0:
            return
        resp = requests.put(
            f"{self.ql_url}/open/envs/enable",
            headers=self.ql_headers(),
            json=[env["id"]],
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"启用环境变量失败: {data}")

    def ql_update_env(self, env: dict[str, Any], value: str) -> None:
        body = {
            "id": env["id"],
            "name": env["name"],
            "value": value,
            "remarks": env.get("remarks") or "淘宝 Cookie（扫码登录自动更新）",
        }
        resp = requests.put(
            f"{self.ql_url}/open/envs",
            headers=self.ql_headers(),
            json=body,
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"更新环境变量失败: {data}")
        self.ql_enable_env(env)

    def ql_create_env(self, name: str, value: str) -> None:
        body = [{
            "name": name,
            "value": value,
            "remarks": "淘宝 Cookie（扫码登录自动创建）",
        }]
        resp = requests.post(
            f"{self.ql_url}/open/envs",
            headers=self.ql_headers(),
            json=body,
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"创建环境变量失败: {data}")
        env = self.ql_find_env(name)
        if env:
            self.ql_enable_env(env)

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

    def merge_cookie(self, old_value: str, new_ck: str) -> str:
        new_id = self.account_id(new_ck)
        old_list = self.split_accounts(old_value)
        merged: list[str] = []
        replaced = False
        for item in old_list:
            if new_id and self.account_id(item) == new_id:
                merged.append(new_ck)
                replaced = True
            else:
                merged.append(item)
        if not replaced:
            merged.append(new_ck)
        return "\n".join(merged)

    def upload_cookie(self, cookie_str: str) -> None:
        if not self.can_upload():
            self.initialize.error_message(
                "未配置 TB_LOGIN_client_id / TB_LOGIN_client_secret，无法上传，仅打印 Cookie"
            )
            self.initialize.info_message(cookie_str)
            return

        self.initialize.info_message(f"连接青龙: {self.ql_url}")
        self.ql_get_token()
        nick = self.account_id(cookie_str) or "未知账号"
        for name in self.targets:
            env = self.ql_find_env(name)
            if env:
                final = self.merge_cookie(env.get("value") or "", cookie_str)
                self.ql_update_env(env, final)
                self.initialize.info_message(f"已更新 {name}（账号 {nick}）", is_flag=True)
            else:
                self.ql_create_env(name, cookie_str)
                self.initialize.info_message(f"已新建 {name}（账号 {nick}）", is_flag=True)

    # ---------- entry ----------

    def run(self) -> None:
        self.initialize.info_message("淘宝扫码登录开始")
        try:
            self.open_login_page()
            qr = self.generate_qr()
            self.log_qr(str(qr["codeContent"]))
            confirmed = self.wait_confirmed(qr["t"], qr["ck"])
            self.initialize.info_message("扫码确认成功，正在收集 Cookie", is_flag=True)
            cookie_str = self.collect_cookies(confirmed)
            nick = self.account_id(cookie_str) or "未知"
            self.initialize.info_message(f"登录账号: {nick}", is_flag=True)
            self.upload_cookie(cookie_str)
        except Exception as exc:
            self.initialize.error_message(f"扫码登录失败: {exc}", is_flag=True)
            raise
        finally:
            self.cleanup_qr_image()
            self.initialize.info_message("淘宝扫码登录结束")
            self.initialize.send_notify("淘宝扫码登录 | https://login.taobao.com/")


if __name__ == "__main__":
    try:
        TaoBaoQrLogin().run()
    except Exception:
        sys.exit(1)
