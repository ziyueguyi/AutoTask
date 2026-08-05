import importlib.util
import logging
import os
import random
import time
from pathlib import Path


class ImportSet:
    def __init__(self, prefix=None, model_list=None):
        """
        :param prefix: 青龙环境变量前缀，如 "BD" → BD_notify / BD_account / BD_switch_delay
        :param model_list: 兼容旧参数，暂未使用
        """
        self.prefix = str(prefix).strip() if prefix else ""
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

    def env_key(self, feature: str) -> str:
        """拼接青龙环境变量名：{prefix}_{feature}。"""
        feature = str(feature).strip()
        if not self.prefix:
            return feature
        return f"{self.prefix}_{feature}"

    def load_accounts(self, feature: str = "account"):
        """
        从青龙环境变量读取账号，默认读取 {prefix}_account。
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

    def send_notify(self, title):
        """
        发送通知。开关读取青龙变量 {prefix}_notify。

        :param title:
        :return:
        """
        config_name = self.env_key("notify")
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
        # 随机延迟：{prefix}_switch_delay
        delay_key = self.env_key("switch_delay")
        switch_delay = os.getenv(delay_key, "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        logging.info(
            f"{'开启' if switch_delay else '未开启'}随机延迟时间，"
            f"可在青龙面板配置环境变量 {delay_key}"
        )
        if switch_delay:
            delay = int(random.uniform(10, 300))
            logging.info(f"开启延迟，{delay}秒后执行代码")
            time.sleep(delay)  # 注释该行代码，即可不会有延迟
