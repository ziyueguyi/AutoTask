# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :Template.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :
"""
from importlib import util
from pathlib import Path

import requests


class Template:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / 'public'
        import_set_spc = util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        self.import_set = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.notify = self.import_set.import_notify()
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session()
        self.init_config()

    def init_config(self):
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")

    def run(self):
        pass

if __name__ == '__main__':
    t = Template()
    t.run()
