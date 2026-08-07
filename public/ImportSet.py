# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :ImportSet.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/27 17:42
# @文件介绍 :导包集合

青龙环境变量约定（传入前缀后生效）：
  ImportSet("BD")              → BD_notify / BD_account
  ImportSet(["TX", "TX_JH"])   → 两边都可配置；后写的前缀优先
                                 （有 TX_JH_account 时 TX_account 不生效）
"""
import importlib.util
import os
from pathlib import Path


def normalize_prefixes(prefix) -> list[str]:
    """支持 "TX" 或 ["TX", "TX_JH"]。"""
    if prefix is None:
        return []
    if isinstance(prefix, (list, tuple, set)):
        return [str(p).strip() for p in prefix if str(p).strip()]
    text = str(prefix).strip()
    return [text] if text else []


class ImportSet:
    def __init__(self, prefix=None):
        """
        :param prefix: 青龙环境变量前缀，如 "BD" 或 ["TX", "TX_JH"]
        """
        self.prefixes = normalize_prefixes(prefix)
        # 兼容旧代码读单一 prefix：取第一个
        self.prefix = self.prefixes[0] if self.prefixes else ""
        self.tools_path = Path(__file__).resolve().parent

    def env_keys(self, feature: str) -> list[str]:
        """按传入顺序返回候选环境变量名。"""
        feature = str(feature).strip()
        if not self.prefixes:
            return [feature] if feature else []
        return [f"{p}_{feature}" for p in self.prefixes]

    def env_key(self, feature: str) -> str:
        """
        当前生效的环境变量名：从后往前找第一个已配置的键；
        都未配置时返回最后一个前缀对应的键。
        """
        keys = self.env_keys(feature)
        if not keys:
            return str(feature).strip()
        for key in reversed(keys):
            val = os.getenv(key)
            if val is not None and str(val).strip() != "":
                return key
        return keys[-1]

    def write_env_key(self, feature: str) -> str:
        """
        写入用的环境变量名：已存在则用当前生效键；
        都未配置时用第一个前缀（主前缀），如 TX_account。
        """
        keys = self.env_keys(feature)
        if not keys:
            return str(feature).strip()
        for key in reversed(keys):
            val = os.getenv(key)
            if val is not None and str(val).strip() != "":
                return key
        return keys[0]

    def get_env(self, feature: str, default: str = "") -> str:
        """读取 feature；多前缀时后写优先。"""
        for key in reversed(self.env_keys(feature)):
            val = os.getenv(key)
            if val is not None and str(val).strip() != "":
                return str(val).strip()
        return default

    def set_env(
        self,
        feature: str,
        value: str,
        *,
        name: str | None = None,
        session=None,
        merge: bool = False,
        merge_fn=None,
        remarks: str = "",
        dedupe: bool = True,
    ):
        """
        写入青龙环境变量（与 get_env 对称）。
        :param feature: 短名，如 account → 默认写入 write_env_key("account")
        :param name: 可选，直接指定完整变量名（跳过前缀解析）
        """
        env_name = (name or "").strip() or self.write_env_key(feature)
        return self.import_qinglong(session=session).set_env(
            env_name,
            value,
            merge=merge,
            merge_fn=merge_fn,
            remarks=remarks,
            dedupe=dedupe,
        )

    def import_notify(self):
        """
        初始化通知
        :return :
        """
        notify_spc = importlib.util.spec_from_file_location('notify', str(self.tools_path / 'tools' / 'notify.py'))
        notify = importlib.util.module_from_spec(notify_spc)
        notify_spc.loader.exec_module(notify)
        return notify.Notify()

    def import_initialize(self):
        """加载 initialize，并传入同一前缀（支持多前缀）。"""
        i_path = str(self.tools_path / 'tools' / 'initialize.py')
        initialize_spc = importlib.util.spec_from_file_location('initialize', i_path)
        initialize = importlib.util.module_from_spec(initialize_spc)
        initialize_spc.loader.exec_module(initialize)
        return initialize.ImportSet(prefix=self.prefixes)

    def import_qinglong(self, session=None):
        """
        加载青龙 Open API（与 proxy / notify 一致：前缀在此解析）。
        读取 {prefix}_ql_url / client_id / client_secret。
        """
        ql_path = str(self.tools_path / 'tools' / 'qinglong.py')
        ql_spc = importlib.util.spec_from_file_location('qinglong', ql_path)
        ql_mod = importlib.util.module_from_spec(ql_spc)
        ql_spc.loader.exec_module(ql_mod)
        return ql_mod.QingLongAPI(
            base_url=self.get_env("ql_url") or "http://127.0.0.1:5700",
            client_id=self.get_env("client_id"),
            client_secret=self.get_env("client_secret"),
            session=session,
        )

    def import_proxy(self):
        """加载代理工具（config_name 已按当前前缀解析，与 notify 一致）。"""
        proxy_path = str(self.tools_path / 'tools' / 'proxy.py')
        proxy_spc = importlib.util.spec_from_file_location('proxy', proxy_path)
        proxy_mod = importlib.util.module_from_spec(proxy_spc)
        proxy_spc.loader.exec_module(proxy_mod)
        return proxy_mod.Proxy(config_name=self.env_key("proxy"))

    def apply_proxy(self, session, initialize=None):
        """
        解析代理并挂到 session（含失败换新重试）。
        :param session: curl_cffi / requests Session
        :param initialize: 可选，用于 info/error 日志；不传则静默
        :return: 当前代理地址；未配置返回空串
        """
        helper = self.import_proxy()
        default_retry = int(getattr(helper, "DEFAULT_RETRY", 2))
        try:
            retries = int(self.get_env("proxy_retry") or str(default_retry))
        except ValueError:
            retries = default_retry

        on_info = None
        on_error = None
        if initialize is not None:
            on_info = lambda msg: initialize.info_message(msg)
            on_error = lambda msg: initialize.error_message(msg, is_flag=True)

        return helper.setup_session(
            session,
            max_retries=retries,
            retry_env=self.env_key("proxy_retry"),
            on_info=on_info,
            on_error=on_error,
        )