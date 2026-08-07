# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :Base.py
# @作者名称 :sxzhang1
# @任务名称：name 样例
# @任务时间：cron: 19 7 * * *
# @目标网站：url: https://baidu.com
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :样例
"""
from importlib import util
from pathlib import Path

from curl_cffi import requests


class Base:
    def __init__(self, suffix='base') -> None:
        tools_path = Path(__file__).resolve().parent
        import_set_spc = util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        import_set = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set)
        self.import_set = import_set.ImportSet(suffix)
        self.initialize = self.import_set.import_initialize()
        self.session = requests.Session(timeout=10, impersonate="chrome")
        self.session.headers.update({
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            "Content-type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        })
        self.import_set.apply_proxy(self.session, self.initialize)

    def run(self):
        self.initialize.info_message("签到开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(
                f"未配置账号，请在青龙面板设置环境变量 {self.initialize.env_key('account')}"
            )
            return
        for ind, sec in enumerate(accounts):
            self.initialize.info_message(f"共{len(accounts)}个账户，第{ind + 1}个账户：{sec},")
            try:
                pass
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("签到结束")
        self.initialize.send_notify("样例")


if __name__ == '__main__':
    Base().run()
