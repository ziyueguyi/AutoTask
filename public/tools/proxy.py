# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :proxy.py
# @作者名称 :sxzhang1
# @日期时间 :2026/8/7 15:55
# @文件介绍 :从青龙环境变量读取代理（与 notify 相同：不管前缀，只读传入的 config_name）

青龙配置（前缀由 ImportSet 决定，如 TX / TJY）：
  {prefix}_proxy = 代理，支持两种写法：

  1) 直连（固定代理）
     http://127.0.0.1:7890
     或 1.2.3.4:7890

  2) 提取 API（请求后返回纯文本 ip:port，再转成 http://ip:port）
     http://api.xiequ.cn/VAD/GetIp.aspx?act=get&uid=你的uid&...其它参数

  {prefix}_proxy_retry = 请求失败后换代理重试次数，默认 2（不含首次）

用法：
  import_set.apply_proxy(session, initialize)   # 推荐：解析前缀 + 挂 session
  # 或
  proxy = import_set.import_proxy()
  proxy.setup_session(session, max_retries=2, retry_env="TX_proxy_retry", on_info=...)
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable

import requests

try:
    from curl_cffi.requests.exceptions import (
        ConnectTimeout,
        ConnectionError as CurlConnectionError,
        InvalidProxyURL,
        ProxyError,
        Timeout,
    )
    _RETRY_EXC: tuple = (
        ProxyError,
        InvalidProxyURL,
        ConnectTimeout,
        CurlConnectionError,
        Timeout,
        ConnectionError,
        OSError,
    )
except ImportError:  # pragma: no cover
    _RETRY_EXC = (ConnectionError, TimeoutError, OSError)

# 直连：http://host:port / socks5://host:port / 纯 ip:port
_DIRECT_PROXY = re.compile(
    r"^(?:"
    r"(?:https?|socks5?h?)://[^/\s?]+:\d+/?"  # 带协议，无路径无 query
    r"|"
    r"\d{1,3}(?:\.\d{1,3}){3}:\d+"  # 纯 ip:port
    r")$",
    re.I,
)
_IP_PORT = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}:\d+)")

DEFAULT_PROXY_RETRY = 2


class Proxy:
    DEFAULT_RETRY = DEFAULT_PROXY_RETRY

    def __init__(self, config_name: str = "proxy") -> None:
        # 一般为 {prefix}_proxy，由 ImportSet.env_key("proxy") 传入
        self.config_name = (config_name or "proxy").strip() or "proxy"
        self._current_proxy = ""

    @staticmethod
    def config_hint(config_name: str = "proxy") -> str:
        """青龙面板代理配置说明。"""
        return (
            f"代理配置：青龙环境变量 {config_name}\n"
            f"  · 直连：http://127.0.0.1:7890 或 1.2.3.4:7890\n"
            f"  · 提取 API：填完整接口 URL，接口需返回纯文本 ip:port\n"
            f"    例：http://api.xiequ.cn/VAD/GetIp.aspx?act=get&uid=你的uid&...\n"
            f"  · 同前缀 proxy_retry（如 TX_proxy_retry）：失败换代理重试次数，"
            f"默认 {DEFAULT_PROXY_RETRY}"
        )

    def raw_value(self) -> str:
        val = os.getenv(self.config_name, "")
        return str(val).strip() if val else ""

    def is_api_source(self) -> bool:
        """环境变量是否为提取 API（非固定直连）。"""
        raw = self.raw_value()
        if not raw or _DIRECT_PROXY.match(raw):
            return False
        return raw.lower().startswith("http://") or raw.lower().startswith("https://")

    @staticmethod
    def to_proxy_url(ip_port: str) -> str:
        text = (ip_port or "").strip()
        if not text:
            return ""
        if text.lower().startswith(("http://", "https://", "socks5://", "socks5h://", "socks4://")):
            return text.rstrip("/")
        return f"http://{text}"

    @classmethod
    def fetch_from_api(cls, api_url: str, timeout: int = 15) -> str:
        """请求提取接口，解析返回的 ip:port，得到 http://ip:port。"""
        resp = requests.get(api_url, timeout=timeout)
        body = (resp.text or "").strip()
        match = _IP_PORT.search(body)
        if not match:
            raise RuntimeError(
                f"代理接口未返回 ip:port，HTTP {resp.status_code}，响应: {body[:200]!r}"
            )
        return cls.to_proxy_url(match.group(1))

    def resolve(self, raw: str) -> str:
        """
        将环境变量原值解析为 session 可用的代理地址。
        - 直连 / 纯 ip:port → 规范化
        - 其它 http(s) URL → 当作提取 API 请求一次
        """
        text = (raw or "").strip()
        if not text:
            return ""
        if _DIRECT_PROXY.match(text):
            return self.to_proxy_url(text)
        if text.lower().startswith("http://") or text.lower().startswith("https://"):
            return self.fetch_from_api(text)
        return text

    def get_proxy(self) -> str:
        """
        读取青龙环境变量并解析；未配置返回空串。
        提取 API 每次调用都会重新请求，拿到新 ip:port。
        """
        raw = self.raw_value()
        if not raw:
            return ""
        return self.resolve(raw)

    def apply_to_session(self, session: Any, proxy: str | None = None) -> str:
        """写入 session.proxies；proxy 为空则先 get_proxy()。"""
        address = (proxy if proxy is not None else self.get_proxy()) or ""
        if address:
            session.proxies.update({"http": address, "https": address})
            self._current_proxy = address
        return address

    def refresh_to_session(
        self,
        session: Any,
        *,
        reason: str = "",
        on_refresh: Callable[[str, str], None] | None = None,
    ) -> str:
        """重新 get_proxy 并写回 session。"""
        new_proxy = self.get_proxy()
        if not new_proxy:
            return ""
        self.apply_to_session(session, new_proxy)
        if on_refresh:
            on_refresh(new_proxy, reason or "refresh")
        return new_proxy

    def attach_session_retry(
        self,
        session: Any,
        *,
        max_retries: int = DEFAULT_PROXY_RETRY,
        on_retry: Callable[[int, int, str, BaseException], None] | None = None,
    ) -> Any:
        """
        给 session 挂代理失败重试：请求因代理/连接失败时，换新代理并重试。

        :param max_retries: 失败后额外重试次数（不含首次）
        """
        if getattr(session, "_autotask_proxy_retry", False):
            return session

        original_request = session.request
        helper = self
        retries = max(0, int(max_retries))

        def request(method, url, **kwargs):
            last_exc: BaseException | None = None
            for attempt in range(retries + 1):
                try:
                    return original_request(method, url, **kwargs)
                except _RETRY_EXC as exc:
                    last_exc = exc
                    if attempt >= retries:
                        break
                    if helper.is_api_source():
                        try:
                            new_proxy = helper.refresh_to_session(session, reason="error")
                        except Exception as refresh_exc:
                            raise RuntimeError(
                                f"代理失效且重新获取失败（{helper.config_name}）: {refresh_exc}"
                            ) from refresh_exc
                        if not new_proxy:
                            break
                        if on_retry:
                            on_retry(attempt + 1, retries, new_proxy, exc)
            assert last_exc is not None
            raise last_exc

        session.request = request  # type: ignore[method-assign]
        session._autotask_proxy_retry = True
        return session

    def setup_session(
        self,
        session: Any,
        *,
        max_retries: int = DEFAULT_PROXY_RETRY,
        retry_env: str = "",
        on_info: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> str:
        """
        解析代理 → 写入 session → 挂失败重试，并输出配置提示。

        :param max_retries: 失败重试次数（不含首次），默认 DEFAULT_PROXY_RETRY
        :param retry_env: 重试次数对应的环境变量全名，如 TX_proxy_retry
        :return: 当前代理地址；未配置返回空串
        """
        proxy_env = self.config_name
        retry_name = (retry_env or "").strip() or "proxy_retry"
        retries = max(0, int(max_retries))

        def _info(msg: str) -> None:
            if on_info:
                on_info(msg)

        def _error(msg: str) -> None:
            if on_error:
                on_error(msg)

        try:
            proxy = self.get_proxy()
        except Exception as exc:
            _error(
                f"代理解析失败（环境变量 {proxy_env}）: {exc}\n"
                f"{self.config_hint(proxy_env)}"
            )
            raise

        if not proxy:
            _info(f"未配置代理（环境变量 {proxy_env}），直连访问")
            return ""

        self.apply_to_session(session, proxy)
        _info(f"已启用代理 {proxy}，代理环境变量：{proxy_env}")

        def _on_retry(attempt, max_r, new_proxy, exc):
            _info(
                f"代理请求失败，更换并重试 {attempt}/{max_r}："
                f"{new_proxy}（{proxy_env}，原因：{exc}）"
            )

        self.attach_session_retry(session, max_retries=retries, on_retry=_on_retry)
        _info(
            f"代理失败重试次数：{retries}"
            f"（配置变量 {retry_name}，默认 {DEFAULT_PROXY_RETRY}）"
        )
        return proxy
