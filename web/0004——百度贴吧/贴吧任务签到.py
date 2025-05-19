# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧任务签到.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 17:11
# @文件介绍 :
new Env('贴吧任务签到')
cron: 19 6 * * *
"""

import json
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests
from fake_useragent import UserAgent  # pip install fake-useragent


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
        """
        账号进行签到
        :param tbs:
        :param user_name:
        :param sec:
        :return:
        """
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

    def get_point(self):
        """
        获取账号积分信息
        :return:
        """
        url = f'{self.baseUrl}/mo/q/usergrowth/showUserGrowth?client_type=2&client_version=12.60.1.2'
        response = self.session.get(url)
        if response.status_code == 200 and response.json().get("no") == 0:
            data = response.json()['data']
            level = list(filter(lambda x: x['is_current'] == 1, data['level_info']))[0]
            points = level['next_level_value'] - level['growth_value']
            self.initialize.info_message(f"当前账号等级：{level['level']}", is_flag=True)
            self.initialize.info_message(f"当前贴贝余额：{data['tmoney']['current']}", is_flag=True)
            self.initialize.info_message(f"当前已有积分：{data['growth_info']['value']}", is_flag=True)
            self.initialize.info_message(f"下级所需积分：{points}", is_flag=True)
        else:
            self.initialize.info_message(f"获取积分失败", is_flag=True)

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
                time.sleep(1)
                self.get_point()
        self.initialize.info_message("贴吧签到结束")
        self.initialize.send_notify("「贴吧签到」")


if __name__ == '__main__':
    PostBar().run()
