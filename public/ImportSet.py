# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :ImportSet.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/27 17:42
# @文件介绍 :导包集合
"""
import importlib.util
from pathlib import Path


class ImportSet:
    def __init__(self, model_list=None):
        self.model_list = model_list if model_list else []
        # 获取当前脚本的上级目录
        self.tools_path = Path(__file__).resolve().parent

    def import_notify(self):
        """
        初始化通知
        :return :
        """
        notify_spc = importlib.util.spec_from_file_location('notify', str(self.tools_path / 'tools' / 'notify.py'))
        notify = importlib.util.module_from_spec(notify_spc)
        notify_spc.loader.exec_module(notify)
        return notify

    def import_initialize(self):
        """"""
        initialize_spc = importlib.util.spec_from_file_location('initialize',
                                                                str(self.tools_path / 'tools' / 'initialize.py'))
        initialize = importlib.util.module_from_spec(initialize_spc)
        initialize_spc.loader.exec_module(initialize)
        return initialize.ImportSet()


    def import_config_option(self):
        config_option_spc = importlib.util.spec_from_file_location('ConfigOption', str(self.tools_path / 'ConfigOption.py'))
        config_option = importlib.util.module_from_spec(config_option_spc)
        config_option_spc.loader.exec_module(config_option)
        return config_option.ConfigOption(Path().resolve())
