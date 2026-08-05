# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :ImportSet.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/4/27 17:42
# @文件介绍 :导包集合

青龙环境变量约定（传入前缀后生效，例如 ImportSet("BD")）：
  - BD_notify   通知开关
  - BD_account  账号
  - BD_功能名   后续功能统一按此前缀扩展
"""
import importlib.util
from pathlib import Path


class ImportSet:
    def __init__(self, prefix=None):
        """
        :param prefix: 青龙环境变量前缀，如 "BD" → BD_notify / BD_account
        """
        self.prefix = str(prefix).strip() if prefix else ""
        self.tools_path = Path(__file__).resolve().parent

    def env_key(self, feature: str) -> str:
        """
        拼接青龙环境变量名：prefix + '_' + feature
        未设置 prefix 时直接返回 feature。
        """
        feature = str(feature).strip()
        if not self.prefix:
            return feature
        return f"{self.prefix}_{feature}"

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
        """加载 initialize，并传入同一前缀。"""
        i_path = str(self.tools_path / 'tools' / 'initialize.py')
        initialize_spc = importlib.util.spec_from_file_location('initialize',i_path)
        initialize = importlib.util.module_from_spec(initialize_spc)
        initialize_spc.loader.exec_module(initialize)
        return initialize.ImportSet(prefix=self.prefix)