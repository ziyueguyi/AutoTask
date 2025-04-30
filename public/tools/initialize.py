import importlib.util
import logging
import random
import time
from pathlib import Path


class ImportSet:
    def __init__(self, model_list=None):
        self.model_list = model_list if model_list else []
        tools_path = Path(__file__).resolve().parent
        # 获取当前脚本的上级目录
        public_path = tools_path.parent
        notify_spc = importlib.util.spec_from_file_location('notify', str(tools_path / 'notify.py'))
        self.notify = importlib.util.module_from_spec(notify_spc)
        notify_spc.loader.exec_module(self.notify)

        config_option_spc = importlib.util.spec_from_file_location('ConfigOption', str(public_path / 'ConfigOption.py'))
        config_option = importlib.util.module_from_spec(config_option_spc)
        config_option_spc.loader.exec_module(config_option)
        self.config_option = config_option.ConfigOption(public_path)
        self.message_list = []  # 存储消息数据

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

    def info_message(self, message_content):
        """
        成功日志输出

        :param message_content:
        :return:
        """
        logging.info(f"🎈{message_content}")
        self.message(f"🎈{message_content}")

    def error_message(self, message_content):
        """
        失败日志输出

        :param message_content:
        :return:
        """
        logging.error(f"😢{message_content}")
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
        发送通知

        :param title:
        :return:
        """
        msg = '\n'.join(self.message_list)
        self.notify.send(title, msg)

    def init(self):
        """
        延迟时间和日志初始化

        :return:
        """
        # 初始化日志
        self.init_logger()
        # 随机延迟
        switch_delay = self.config_option.read_config_key("系统配置", "switch_delay", field_type=bool)
        logging.info(f"{'开启' if switch_delay else '未开启'}随机延迟时间，config.json里面switch_delay可以配置")
        if switch_delay:
            delay = int(random.uniform(10, 300))
            logging.info(f"开启延迟，{delay}秒后执行代码")
            time.sleep(delay)  # 注释该行代码，即可不会有延迟
