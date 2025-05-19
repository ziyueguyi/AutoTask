# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧任务签到.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 17:11
# @文件介绍 :
new Env('贴吧任务签到')
cron: 19 7 * * *
"""

import hashlib
import json
import random
import time
from importlib import util
from pathlib import Path
from fake_useragent import UserAgent  # pip install fake-useragent
from curl_cffi import requests


class PostBar:
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
        self.session.headers.update({
            'connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'tieba.baidu.com',
            'charset': 'UTF-8',
            'User-Agent': UserAgent().chrome,
        })
        self.init_config()
        self.baseUrl = 'https://tieba.baidu.com'

    def init_config(self):
        """
        初始化方法
        :return:
        """
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")

    def get_user_info(self):
        user_url = f'{self.baseUrl}/mo/q/usergrowth/showUserGrowth?client_type=2&client_version=12.60.1.2'
        response = self.session.get(user_url)
        if response.status_code == 200 and response.json():
            data = response.json()['data']
            user_name = data['user']['uname']
            tbs = data['tbs']
            self.initialize.info_message(f"昵称：{user_name}")
            return user_name, tbs
        else:
            self.initialize.info_message(f"获取用户信息失败", is_flag=True)
            return None, None

    def sign(self, tbs, user_name, sec):
        params = {
            'tbs': tbs,
            'act_type': 'page_sign',
            'cuid': json.loads(self.config_option.read_config_key(section=sec, key="cookies")).get("CUID"),
            'client_type': 2,
            'brand': 'OPPO',
            'model': 'OPPO%20R9s',
            'zid': '',
            'clientVersion': '12.60.1.2',
            'clientType': '2'
        }
        url = f'{self.baseUrl}/mo/q/usergrowth/commitUGTaskInfo'
        response = self.session.post(url, params=params)
        if response.status_code == 200 and response.json().get("no") == 0:
            self.initialize.info_message(f"{user_name}签到成功", is_flag=True)
        else:
            self.initialize.info_message(f"{user_name}签到失败", is_flag=True)

    def run(self):
        self.initialize.info_message("贴吧签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            user_name, tbs = self.get_user_info()
            if user_name:
                time.sleep(1)
                self.sign(tbs, user_name, sec)
        self.initialize.info_message("贴吧签到结束")
        self.initialize.send_notify("「贴吧」")


if __name__ == '__main__':
    PostBar().run()
