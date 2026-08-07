# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :tx_login.py
# @文件介绍 :淘宝 PC 扫码登录，日志打印二维码，确认后回写青龙 Cookie
# 青龙环境变量（前缀 TX_LOGIN / TX）：
#   TX_LOGIN_client_id      青龙应用 Client ID（与 secret 同时配置才可上传）
#   TX_LOGIN_client_secret  青龙应用 Client Secret
#   TX_LOGIN_ql_url         青龙地址，默认 http://127.0.0.1:5700
#   TX_LOGIN_target         写入的环境变量名，默认 TX_account（覆盖写入，不追加）
#   TX_LOGIN_merge          填 1 时按账号 unb 合并多账号；默认覆盖整段 Cookie
#   TX_LOGIN_notify         通知开关，填 1 开启
#   TX_LOGIN_timeout        等待扫码超时秒数，默认 300
# 依赖：curl_cffi、qrcode
const $ = new Env('淘宝扫码登录')
cron: 1 1 1 1 1
"""
from __future__ import annotations

import io
import os
import re
import struct
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from public.Base import Base


class TxLogin(Base):
    def __init__(self) -> None:
        super().__init__(["TX", "TX_JH", "TX_LOGIN"])
        self.session.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh,zh-CN;q=0.9",
            "referer": "https://www.taobao.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
            ),
        })

        self.ql = self.import_set.import_qinglong()
        self.LOGIN_HOST = "https://login.taobao.com"
        self.RETURN_URL = "https://www.taobao.com/"
        self.qr_path = Path(__file__).resolve().parent / "tx_login_qr.bmp"
        self.login_page_url = f"{self.LOGIN_HOST}/havanaone/login/login.htm?bizName=taobao&f=top&redirectURL={self.RETURN_URL}"
        self._csrf = ""

    # ---------- utils ----------

    @staticmethod
    def cookies_to_str(cookies: dict[str, str], keys: list[str] | None = None) -> str:
        if keys:
            seen: set[str] = set()
            items: list[tuple[str, str]] = []
            for k in keys:
                if cookies.get(k) and k not in seen:
                    items.append((k, cookies[k]))
                    seen.add(k)
            for k, v in cookies.items():
                if k in seen or v is None or str(v) == "":
                    continue
                # 跳过明显非业务字段
                if k.lower().startswith(("aria", "xsrf", "arms_")):
                    continue
                items.append((k, str(v)))
                seen.add(k)
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
        for key in ("unb", "tracknick", "lgc", "_nk_", "dnk", "lid"):
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
            try:
                jar.update({k: str(v) for k, v in dict(self.session.cookies).items()})
            except Exception:
                pass
        return jar

    def apply_cookies(self, cookies: dict[str, str]) -> None:
        for name, value in cookies.items():
            if not name or value is None:
                continue
            value = str(value)
            for domain in (".taobao.com", ".tmall.com", "login.taobao.com", "h5api.m.taobao.com"):
                try:
                    self.session.cookies.set(name, value, domain=domain)
                except Exception:
                    try:
                        self.session.cookies.set(name, value)
                    except Exception:
                        pass

    @classmethod
    def cookies_from_async_url(cls, url: str) -> dict[str, str]:
        """pass.tmall.com/add 等链接把登录 Cookie 放在 query 里。"""
        query = parse_qs(urlparse(str(url)).query, keep_blank_values=True)
        result: dict[str, str] = {}
        skip = {"target", "login", "tmsc", "opi", "pacc", "_l_g_", "cancelledSubSites", }
        for key, values in query.items():
            if not values or key in skip:
                continue
            result[key] = values[0]
        # uc1=pas=0;cookie14=... 需拆开
        uc1 = result.get("uc1") or ""
        if ";" in uc1 and "=" in uc1:
            for part in uc1.split(";"):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    result.setdefault(k.strip(), v.strip())
        return result

    @staticmethod
    def _split_set_cookie_header(raw: str) -> list[str]:
        """把可能被合并的 Set-Cookie 拆成单条（Expires 含逗号，不能简单 split(',')）。"""
        text = str(raw or "").strip()
        if not text:
            return []
        # 下一条 cookie 通常形如 ", name=value"
        return [p.strip() for p in re.split(r",(?=\s*[^;,=\s]+=)", text) if p.strip()]

    @classmethod
    def cookies_from_set_cookie_values(cls, raw_list: list) -> dict[str, str]:
        jar: dict[str, str] = {}
        for item in raw_list:
            for piece in cls._split_set_cookie_header(str(item)):
                part = piece.split(";", 1)[0].strip()
                if "=" not in part:
                    continue
                k, v = part.split("=", 1)
                name = k.strip()
                # 跳过删除型空值（如 sn=）
                if not name:
                    continue
                jar[name] = v.strip()
        return jar

    @classmethod
    def cookies_from_response(cls, resp) -> dict[str, str]:
        jar: dict[str, str] = {}
        try:
            for name, value in dict(resp.cookies).items():
                jar[str(name)] = str(value)
        except Exception:
            pass

        headers = getattr(resp, "headers", None) or {}
        raw_list: list = []
        for getter in ("get_list", "getlist", "get_all"):
            if hasattr(headers, getter):
                try:
                    raw_list = getattr(headers, getter)("set-cookie") or getattr(headers, getter)("Set-Cookie") or []
                except Exception:
                    raw_list = []
                if raw_list:
                    break
        if not raw_list:
            # curl_cffi / httpx 有时把多条塞进一个字符串
            single = None
            try:
                single = headers.get("set-cookie") or headers.get("Set-Cookie")
            except Exception:
                single = None
            if single:
                raw_list = [single] if isinstance(single, str) else list(single)

        jar.update(cls.cookies_from_set_cookie_values(raw_list))

        # 跟随重定向链上的 Set-Cookie
        try:
            for hist in getattr(resp, "history", None) or []:
                jar.update(cls.cookies_from_response(hist))
        except Exception:
            pass
        return jar

    def ingest_response_cookies(self, resp) -> dict[str, str]:
        got = self.cookies_from_response(resp)
        if got:
            self.apply_cookies(got)
        return got

    def refresh_m_h5_tk(self, base: dict[str, str] | None = None) -> dict[str, str]:
        """访问 h5api 触发下发 _m_h5_tk / _m_h5_tk_enc。"""
        got: dict[str, str] = {}
        jar = dict(base or self.session_cookie_dict())
        cookie_header = self.cookies_to_str(jar)
        headers = {
            "referer": "https://www.taobao.com/",
            "accept": "*/*",
            "origin": "https://www.taobao.com",
        }
        if cookie_header:
            headers["cookie"] = cookie_header

        # 淘宝首页会打的 recommend 接口，无有效 sign 也会下发 _m_h5_tk
        ts = str(int(time.time() * 1000))
        recommend_data = (
            '{"appId":"43908","params":"{\\"referer\\":\\"pc_taobao\\",'
            '\\"hng\\":\\"\\",\\"fromSource\\":\\"wotao\\"}"}'
        )
        endpoints = [
            (
                "https://h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend/2.0/",
                {
                    "jsv": "2.7.2",
                    "appKey": "12574478",
                    "t": ts,
                    "sign": "0",
                    "api": "mtop.relationrecommend.WirelessRecommend.recommend",
                    "v": "2.0",
                    "timeout": "10000",
                    "type": "jsonp",
                    "dataType": "jsonp",
                    "callback": "mtopjsonp1",
                    "data": recommend_data,
                },
            ),
            (
                "https://h5api.m.taobao.com/h5/mtop.common.getTimestamp/1.0/",
                {
                    "jsv": "2.6.1",
                    "appKey": "12574478",
                    "t": str(int(time.time() * 1000)),
                    "api": "mtop.common.getTimestamp",
                    "v": "1.0",
                    "type": "json",
                    "dataType": "json",
                    "data": "{}",
                },
            ),
            ("https://www.taobao.com/", None),
        ]
        for url, params in endpoints:
            try:
                if params is None:
                    resp = self.session.get(url, headers=headers, allow_redirects=True)
                else:
                    resp = self.session.get(url, params=params, headers=headers, allow_redirects=True)
                got.update(self.ingest_response_cookies(resp))
                if got.get("_m_h5_tk"):
                    self.initialize.info_message(
                        f"已获取 _m_h5_tk（via {urlparse(url).path}）"
                    )
            except Exception as exc:
                self.initialize.error_message(f"刷新 h5 token 失败 {url}: {exc}")
            got.update(self.session_cookie_dict())
            if got.get("_m_h5_tk") and got.get("_m_h5_tk_enc"):
                break
            cookie_header = self.cookies_to_str({**jar, **got})
            if cookie_header:
                headers["cookie"] = cookie_header
        return got

    def collect_cookies(self, confirmed: dict[str, Any], confirmed_cookies: dict[str, str] | None = None) -> str:
        jar: dict[str, str] = self.session_cookie_dict()
        if confirmed_cookies:
            jar.update(confirmed_cookies)
            self.apply_cookies(confirmed_cookies)
            self.initialize.info_message(
                f"CONFIRMED Set-Cookie 字段: {sorted(confirmed_cookies.keys())}"
            )

        async_urls = list(confirmed.get("asyncUrls") or [])
        self.initialize.info_message(f"asyncUrls 数量: {len(async_urls)}")

        # 1) 从 asyncUrls 的 query 抽取登录 Cookie（关键字段都在这里）
        for url in async_urls:
            extracted = self.cookies_from_async_url(str(url))
            if extracted:
                jar.update(extracted)
                self.apply_cookies(extracted)
                self.initialize.info_message(
                    f"从 asyncUrl 解析到 Cookie 字段: {sorted(extracted.keys())}"
                )
            try:
                resp = self.session.get(str(url), allow_redirects=True)
                jar.update(self.ingest_response_cookies(resp))
            except Exception as exc:
                self.initialize.error_message(f"同步站点 Cookie 失败: {exc}")

        # 2) 跳转回淘宝
        redirect = confirmed.get("redirectUrl") or confirmed.get("returnUrl") or self.RETURN_URL
        try:
            resp = self.session.get(str(redirect), allow_redirects=True)
            jar.update(self.ingest_response_cookies(resp))
        except Exception as exc:
            self.initialize.error_message(f"访问跳转页失败: {exc}")

        jar.update(self.session_cookie_dict())
        self.apply_cookies(jar)

        # 3) 专门拉取 _m_h5_tk（扫码响应本身不下发该字段）
        jar.update(self.refresh_m_h5_tk(jar))
        jar.update(self.session_cookie_dict())

        important_cookie_keys = [
            "cookie2",
            "cookie1",
            "cookie17",
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
            "lid",
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
            "sg",
            "csg",
            "skt",
            "uc1",
            "uc3",
            "uc4",
        ]
        cookie_str = self.cookies_to_str(jar, important_cookie_keys)
        keys = list(self.parse_cookie_str(cookie_str).keys())
        self.initialize.info_message(f"最终 Cookie 字段({len(keys)}): {keys}")
        if "cookie2" not in jar:
            raise RuntimeError("登录后未拿到 cookie2，Cookie 不完整")
        if not jar.get("_m_h5_tk"):
            self.initialize.error_message(
                "未拿到 _m_h5_tk，mtop 接口可能不可用；已写入现有 Cookie，可稍后重试登录或手动补全"
            )
        return cookie_str

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
                "缺少依赖 qrcode，请在青龙「依赖管理」安装：qrcode"
            ) from exc

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=2,
        )
        qr.add_data(content)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        self.qr_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_qr_bmp(matrix, self.qr_path, scale=10)
        return self.qr_path

    @staticmethod
    def _write_qr_bmp(matrix: list, path: Path, scale: int = 10) -> None:
        """纯标准库写 BMP，不依赖 pillow。"""
        rows = len(matrix)
        cols = len(matrix[0]) if rows else 0
        width = cols * scale
        height = rows * scale
        row_stride = (width * 3 + 3) & ~3
        pixel_size = row_stride * height
        header_size = 14 + 40
        file_size = header_size + pixel_size

        pixels = bytearray(pixel_size)
        for y in range(rows):
            for x in range(cols):
                # matrix True = 黑模块
                color = 0 if matrix[y][x] else 255
                for dy in range(scale):
                    # BMP 自下而上
                    py = height - 1 - (y * scale + dy)
                    offset = py * row_stride + x * scale * 3
                    for dx in range(scale):
                        i = offset + dx * 3
                        pixels[i:i + 3] = bytes((color, color, color))

        with path.open("wb") as f:
            f.write(b"BM")
            f.write(struct.pack("<IHHI", file_size, 0, 0, header_size))
            f.write(struct.pack(
                "<IiiHHIIiiII",
                40,
                width,
                height,
                1,
                24,
                0,
                pixel_size,
                2835,
                2835,
                0,
                0,
            ))
            f.write(pixels)

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
        resp = self.session.get(
            f"{self.LOGIN_HOST}/havanaone/loginLegacy/qrCode/generate.do",
            params=params,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = ((payload.get("content") or {}).get("data") or {})
        if payload.get("hasError") or not data.get("ck") or not data.get("codeContent"):
            raise RuntimeError(f"生成二维码失败: {payload}")
        return data

    def query_qr(self, t: Any, ck: str) -> tuple[dict[str, Any], dict[str, str]]:
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
            "navUserAgent": self.session.headers.get("User-Agent", ""),
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
            f"{self.LOGIN_HOST}/havanaone/loginLegacy/qrCode/query.do"
            "?bizEntrance=taobao_pc&bizName=taobao",
            data=body,
            headers=headers,
        )
        resp.raise_for_status()
        # CONFIRMED 时会下发大量 Set-Cookie（unb/sgcookie/tracknick 等），
        # curl_cffi 会话 jar 常丢 SameSite=None，必须手动解析
        got = self.ingest_response_cookies(resp)
        payload = resp.json()
        data = ((payload.get("content") or {}).get("data") or {})
        if payload.get("hasError"):
            raise RuntimeError(f"查询扫码状态失败: {payload}")
        return data, got

    def wait_confirmed(self, t: Any, ck: str) -> tuple[dict[str, Any], dict[str, str]]:
        try:
            timeout = int(self.initialize.get_env("timeout") or "300")
        except ValueError:
            timeout = 300
        poll_interval = 10
        deadline = time.time() + timeout
        round_no = 0
        self.initialize.info_message(
            f"开始轮询扫码状态，间隔 {poll_interval}s，超时 {timeout}s"
        )
        while time.time() < deadline:
            round_no += 1
            remain = max(0, int(deadline - time.time()))
            data, got = self.query_qr(t, ck)
            status = str(data.get("qrCodeStatus") or "")
            msg = data.get("titleMsg") or status or "未知状态"
            self.initialize.info_message(
                f"[{round_no}] 扫码状态: {status}（{msg}），剩余约 {remain}s"
            )
            if status == "CONFIRMED":
                # 手机已确认即视为成功；勿再轮询，否则下一轮常变成 EXPIRED
                login_result = data.get("loginResult") or "success"
                self.initialize.info_message(
                    f"扫码确认成功（loginResult={login_result}）",
                    is_flag=True,
                )
                return data, got
            if status == "EXPIRED":
                raise TimeoutError(f"二维码超时（EXPIRED）：{msg}")
            if status in {"CANCELED", "CANCELLED", "TIMEOUT"}:
                raise RuntimeError(f"扫码已取消或超时: {status}（{msg}）")
            time.sleep(poll_interval)
        raise TimeoutError(f"等待扫码超时（{timeout}s）")

    # ---------- qinglong ----------

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
        """多账号合并：同 unb/昵称则替换，否则追加。"""
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
        if not self.ql.ready:
            self.initialize.error_message(
                "未读到青龙上传秘钥，无法写入环境变量，仅打印 Cookie。"
                f"当前 client_id={'有' if self.ql.client_id else '无'}，"
                f"client_secret={'有' if self.ql.client_secret else '无'}。"
                "请在青龙「环境变量」新建（不是只建应用）："
                "TX_LOGIN_client_id / TX_LOGIN_client_secret，"
                "或通用 QL_CLIENT_ID / QL_CLIENT_SECRET；值填应用里的 Client ID/Secret，并确保已启用。"
            )
            self.initialize.info_message(cookie_str)
            return

        self.initialize.info_message(f"连接青龙: {self.ql.base_url}")
        nick = self.account_id(cookie_str) or "未知账号"
        remarks = "淘宝 Cookie（扫码登录自动更新）"
        merge_mode = self.initialize.get_env("merge").lower() in {
            "1", "true", "yes",
        }
        target_raw = self.initialize.get_env("target").strip()
        if target_raw:
            targets = [
                x.strip() for x in target_raw.replace("，", ",").split(",") if x.strip()
            ]
        else:
            targets = [None]  # None → 按前缀写入 env_key("account")
        for name in targets:
            result = self.import_set.set_env(
                "account",
                cookie_str,
                name=name,
                merge=merge_mode,
                merge_fn=self.merge_cookie if merge_mode else None,
                remarks=remarks,
                dedupe=True,
            )
            env_name = name or self.import_set.write_env_key("account")
            if result.get("deleted"):
                self.initialize.info_message(
                    f"已删除重复的 {env_name} ×{result['deleted']}"
                )
            action_map = {
                "created": "已新建",
                "updated": "已覆盖更新",
                "merged": "已合并更新",
            }
            label = action_map.get(result.get("action"), "已更新")
            self.initialize.info_message(f"{label} {env_name}（账号 {nick}）", is_flag=True)

    # ---------- entry ----------

    def run(self) -> None:
        self.initialize.info_message("淘宝扫码登录开始")
        try:
            self.open_login_page()
            qr = self.generate_qr()
            self.log_qr(str(qr["codeContent"]))
            confirmed, confirmed_cookies = self.wait_confirmed(qr["t"], qr["ck"])
            self.initialize.info_message("扫码确认成功，正在收集 Cookie", is_flag=True)
            cookie_str = self.collect_cookies(confirmed, confirmed_cookies)
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
        TxLogin().run()
    except Exception:
        sys.exit(1)
