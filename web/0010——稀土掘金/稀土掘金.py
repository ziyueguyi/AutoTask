# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :稀土掘金.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 17:49
# @文件介绍 :
const $ = new Env('贴吧任务签到')
cron: 22 6 * * *
"""
import json
import time
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        })
        self.init_config()
        self.baseUrl = 'https://api.juejin.cn'

    def init_config(self):
        """
        初始化方法
        :return:
        """
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0").write_config("账户1", "cookies", "").write_config(
                "账户1", "params", "")

    def get_cookies_status(self):
        """
        获取cookies状态
        :return:
        """
        response = self.session.get(f"{self.baseUrl}/growth_api/v1/get_today_status")
        if response.status_code == 200 and response.json()["err_no"] == 403:
            self.initialize.error_message("稀土掘金签到结束", is_flag=True)
            raise Exception("Cookie 已失效")

    def get_user_info(self, params):
        """
        获取用户信息
        :param params
        :return:
        """

        json_data = {
            'pack_req': {
                'user_counter': True,
                'user_growth_info': True,
                'user': True,
            },
        }
        response = self.session.post(
            f'{self.baseUrl}/user_api/v1/user/get_info_pack',
            params={
                'aid': params.get("aid"),
            },
            json=json_data,
        )
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"签到账号：{response.json()['data']['user_basic']['user_name']}", is_flag=True)
            return True
        else:
            self.initialize.error_message("获取用户信息失败", is_flag=True)
            return False

    def sign_in(self, params):
        response = self.session.post("https://api.juejin.cn/growth_api/v1/check_in", json={}, params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"签到成功", is_flag=True)
            self.initialize.info_message(f"获得矿石：{response.json()['data']['incr_point']}颗", is_flag=True)
        elif response.status_code == 200 and response.json()["err_no"] == 15001:
            self.initialize.info_message("今日已签到", is_flag=True)
            self.initialize.info_message(f"获得矿石：-颗", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def get_ore_num(self,params):
        response = self.session.get("https://api.juejin.cn/growth_api/v1/get_cur_point", params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"矿石总量：{response.json()['data']}颗", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def get_sign_day(self,params):
        response = self.session.get("https://api.juejin.cn/growth_api/v1/get_counts", params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"连续签到：{response.json()['data']['cont_count']}天", is_flag=True)
            self.initialize.info_message(f"累计签到：{response.json()['data']['sum_count']}天", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def run(self):
        self.initialize.info_message("稀土掘金签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            try:
                cookies = self.config_option.read_config_key(section=sec, key="cookies")
                params = json.loads(self.config_option.read_config_key(section=sec, key="params"))
                self.session.cookies.update({'sid_tt': cookies, 'sessionid': cookies, 'sessionid_ss': cookies})
                self.get_cookies_status()
                time.sleep(1)

                if self.get_user_info(params):
                    time.sleep(1)

                    self.sign_in(params)
                    time.sleep(1)
                    self.get_ore_num(params)
                    time.sleep(1)
                    self.get_sign_day(params)
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("稀土掘金签到结束")
        self.initialize.send_notify("「稀土掘金」")


if __name__ == '__main__':
    Template().run()
