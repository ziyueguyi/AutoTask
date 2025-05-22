# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :百度网盘.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/20 11:40
# @文件介绍 :网页登录百度网盘svip账号，只需要BDUSS_BFESS和STOKEN即可：{"BDUSS_BFESS":"","STOKEN":""}
const $ = new Env('百度网盘')
cron: 19 7 * * *
"""
import json
import re
import time
from datetime import datetime
from importlib import util
from pathlib import Path

import requests


class Template:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(tools_path / "ImportSet.py"))
        self.import_set = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        })
        self.init_config()

    def init_config(self):
        """
        初始化方法
        :return:
        """
        if not Path.exists(Path.joinpath(self.config_option.file_path, "config.ini")):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")
            self.initialize.info_message("请配置账户信息")
            exit()

    def get_user_info(self):
        """
        获取会员信息
        :return:
        """

        url = "https://pan.baidu.com/api/loginStatus"
        params = {
            "clienttype": "1",
            "app_id": "250528",
            "web": "1",
            "channel": "web",
            "version": "0",
        }
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            if response.json().get("errno") == 0:
                username = response.json().get("login_info").get("username")
                vip_level = response.json().get("login_info").get("vip_level")
                vip_point = response.json().get("login_info").get("vip_point")
                self.initialize.info_message(f"当前账号: {username}", is_flag=True)
                self.initialize.info_message(f"当前等级: {vip_level}", is_flag=True)
                self.initialize.info_message(f"当前经验: {vip_point}", is_flag=True)
                return True
            elif response.json().get("errno") == 36003:
                self.initialize.error_message("cookies失效", is_flag=True)
            else:
                self.initialize.error_message(f"获取用户信息失败: {response.text}", is_flag=True)
        else:
            self.initialize.error_message(f"获取用户信息失败: {response.text}")
        return False

    def sign(self):
        """
        签到程序
        :return:
        """
        url = "https://pan.baidu.com/rest/2.0/membership/level"
        params = {"app_id": "250528", "web": "5", "method": "signin"}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("error_code") == 0:
                self.initialize.info_message(f"签到积分: {data.get('result').get('points')}", is_flag=True)
            elif data.get("error_code") == 421003:
                self.initialize.error_message(f"签到失败：该账号不是svip", is_flag=True)
            elif data.get("error_code") == 421001:
                self.initialize.error_message(f"签到失败：请勿重复签到", is_flag=True)
            # 只有当有错误信息时才输出
            else:
                self.initialize.error_message(f"签到失败：{data.get('show_msg')}", is_flag=True)
        else:
            self.initialize.error_message(f"签到失败： {response.text}", is_flag=True)

    def get_daily_question(self):
        """
        获取问答题
        :return:
        """
        url = "https://pan.baidu.com/act/v2/membergrowv2/getdailyquestion"
        params = {"app_id": "250528", "web": "5"}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            data = response.json().get("data")
            self.initialize.info_message(f"日常问题: {data.get('question')}")
            return data.get("answer"), data.get("ask_id")
        else:
            self.initialize.error_message(f"获取日常问题失败{response.text}")
            return None, None

    def answer_question(self, answer, ask_id):
        """
        回答问题
        :param answer:
        :param ask_id:
        :return:
        """
        url = "https://pan.baidu.com/act/v2/membergrowv2/answerquestion"
        params = {"app_id": "250528", "web": "5", "answer": answer, "ask_id": ask_id}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            if response.json().get("errno") == 0:
                self.initialize.info_message(f"问题积分：{response.json().get('data').get('score')}", is_flag=True)
            elif response.json().get("errno") == 9502:
                self.initialize.error_message(f"回答失败:已超出当天回答上限", is_flag=True)
            else:
                self.initialize.error_message(f"回答失败: {response.json().get('show_msg')}", is_flag=True)
        else:
            self.initialize.error_message(f"获取问题结果失败: {response.text}", is_flag=True)

    def get_vip_end_date(self):
        """
        获取会员到期日期
        :return:
        """

        params = {
            "method": "query",
            "clienttype": "0",
            "app_id": "250528",
            "web": "1",
        }
        response = self.session.get(
            "https://pan.baidu.com/rest/2.0/membership/user", params=params
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("error_code") == 0:
                vip_info = list(filter(lambda x: x.get("detail_cluster") == "svip", data.get("product_infos")))
                if vip_info and vip_info[0].get("status") == 0:
                    self.initialize.info_message(f"到期时间: {self.td(vip_info[0].get('end_time'))}", is_flag=True)
                else:
                    self.initialize.error_message(f"到期时间: 已过期", is_flag=True)
                return
            else:
                self.initialize.info_message(f"获取会员到期时间失败: {response.text}", is_flag=True)
        else:
            self.initialize.error_message(f"获取会员到期时间失败: {response.text}", is_flag=True)
        print(response.json())

    @staticmethod
    def td(ts):
        """
        将时间戳转换为日期时间
        :param ts:
        :return:
        """
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")

    def run(self):
        self.initialize.info_message("签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec}")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                if self.get_user_info():
                    self.get_vip_end_date()
                    time.sleep(1)
                    self.sign()
                    time.sleep(1)
                    answer, ask_id = self.get_daily_question()
                    if answer and ask_id:
                        time.sleep(3)
                        self.answer_question(answer, ask_id)
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("签到结束")
        self.initialize.send_notify("百度网盘")


if __name__ == "__main__":
    Template().run()
