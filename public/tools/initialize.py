# -*- coding: utf-8 -*-
import importlib.util
import logging
import os
import random
import time
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
    def __init__(self, prefix=None, model_list=None):
        """
        :param prefix: 青龙环境变量前缀，如 "BD" 或 ["TX", "TX_JH"]
                       多前缀时后写的优先：有 TX_JH_xxx 则 TX_xxx 不生效
        :param model_list: 兼容旧参数，暂未使用
        """
        self.prefixes = normalize_prefixes(prefix)
        self.prefix = self.prefixes[0] if self.prefixes else ""
        self.model_list = model_list if model_list else []
        tools_path = Path(__file__).resolve().parent
        notify_spc = importlib.util.spec_from_file_location('notify', str(tools_path / 'notify.py'))
        self.notify = importlib.util.module_from_spec(notify_spc)
        notify_spc.loader.exec_module(self.notify)
        account_loader_spc = importlib.util.spec_from_file_location(
            'account_loader',
            str(tools_path / 'account_loader.py'),
        )
        self.account_loader = importlib.util.module_from_spec(account_loader_spc)
        account_loader_spc.loader.exec_module(self.account_loader)
        self.message_list = []  # 存储消息数据
        self.init()

    def env_keys(self, feature: str) -> list[str]:
        """按传入顺序返回候选环境变量名。"""
        feature = str(feature).strip()
        if not self.prefixes:
            return [feature] if feature else []
        return [f"{p}_{feature}" for p in self.prefixes]

    def env_key(self, feature: str) -> str:
        """
        当前生效的环境变量名：从后往前找第一个已配置的键；
        都未配置时返回最后一个前缀对应的键（便于报错提示）。
        """
        keys = self.env_keys(feature)
        if not keys:
            return str(feature).strip()
        for key in reversed(keys):
            val = os.getenv(key)
            if val is not None and str(val).strip() != "":
                return key
        return keys[-1]

    def get_env(self, feature: str, default: str = "") -> str:
        """读取 feature 对应环境变量；多前缀时后写优先。"""
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
        实际调用 ImportSet.set_env / 青龙 Open API。
        """
        tools_path = Path(__file__).resolve().parent.parent
        import_set_spc = importlib.util.spec_from_file_location(
            "ImportSet", str(tools_path / "ImportSet.py")
        )
        import_set_mod = importlib.util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_mod)
        return import_set_mod.ImportSet(self.prefixes).set_env(
            feature,
            value,
            name=name,
            session=session,
            merge=merge,
            merge_fn=merge_fn,
            remarks=remarks,
            dedupe=dedupe,
        )

    def load_accounts(self, feature: str = "account"):
        """
        从青龙环境变量读取账号，默认读取 {prefix}_account。
        多前缀时只读生效的那一条（后写优先）。
        """
        return self.account_loader.load_accounts(self.env_key(feature))

    @staticmethod
    def init_logger():
        """
        初始化日志系统

        :return:
        """
        log = logging.getLogger()
        log.setLevel(logging.INFO)
        log_format = logging.Formatter(
            '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s'
        )

        # Console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(log_format)
        log.addHandler(ch)

    def info_message(self, message_content, is_flag=False):
        """
        成功日志输出

        :param message_content:
        :param is_flag:是否记录该日志，等发送的时候一并发送出去
        :return:
        """
        logging.info(f"🎈{message_content}")
        if is_flag:
            self.message(f"🎈{message_content}")

    def error_message(self, message_content, is_flag=False):
        """
        失败日志输出

        :param message_content:
        :param is_flag:是否记录该日志，等发送的时候一并发送出去
        :return:
        """
        logging.error(f"😢{message_content}")
        if is_flag:
            self.message(f"😢{message_content}")

    def message(self, message_content):
        """
        日志和消息放在一起

        :param message_content:
        :return:
        """
        self.message_list.append(message_content)

    def send_notify(self, title, notify_feature=None):
        """
        发送通知。默认开关 {prefix}_notify。
        若传入 notify_feature（如 sign_notify），且该变量已配置，则优先用 {prefix}_{notify_feature}，
        否则回退到 {prefix}_notify（便于多脚本共用 Cookie、通知可共用或分脚本）。

        :param title:
        :param notify_feature: 可选，如 "sign_notify" / "task_notify"
        :return:
        """
        config_name = self.env_key("notify")
        if notify_feature:
            specific = str(notify_feature).strip()
            if self.get_env(specific):
                config_name = self.env_key(specific)
        msg = '\n'.join(self.message_list)
        self.notify.Notify().send(
            f"【{title}】",
            msg,
            project_name=title,
            config_name=config_name,
        )

    def init(self):
        """
        延迟时间和日志初始化

        :return:
        """
        # 初始化日志
        self.init_logger()
        # 随机延迟：{prefix}_switch_delay（多前缀后写优先）
        delay_key = self.env_key("switch_delay")
        switch_delay = self.get_env("switch_delay", "0").lower() in {
            "1", "true", "yes", "on"
        }
        hint_keys = " / ".join(self.env_keys("switch_delay")) or delay_key
        logging.info(
            f"{'开启' if switch_delay else '未开启'}随机延迟时间，"
            f"可在青龙面板配置环境变量 {hint_keys}"
        )
        if switch_delay:
            delay = int(random.uniform(10, 300))
            logging.info(f"开启延迟，{delay}秒后执行代码")
            time.sleep(delay)  # 注释该行代码，即可不会有延迟
