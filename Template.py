# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :Template.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :
const $ = new Env('贴吧任务签到')
cron: 19 7 * * *
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
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            "Content-type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        })
        self.init_config()

    def init_config(self):
        """
        初始化方法
        :return:
        """
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")
            self.initialize.info_message("请配置账户信息")
            exit()

    def run(self):
        self.initialize.info_message("")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            try:
                pass
            except Exception as e:
                self.initialize.error_message(e)
        self.initialize.info_message("")
        self.initialize.send_notify("")


if __name__ == '__main__':
    Template().run()
