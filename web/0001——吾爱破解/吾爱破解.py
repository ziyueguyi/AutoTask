#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: 吾爱破解.py
Author: WFRobert
Date: 2023/3/9 15:01
cron: 0 25 6 * * ?
new Env('吾爱破解');
Description: 52pojie自动签到,实现每日自动签到52pojie
const $ = new Env('吾爱破解')
cron: 19 7 * * *
"""
import json

from bs4 import BeautifulSoup
from lxml import html

from importlib import util
from pathlib import Path

from curl_cffi import requests


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
        url = "http://{0}:{1}".format('114.231.45.243','8089')
        urls = "https://{0}:{1}".format('114.231.45.243','8089')
        self.session.proxies.update({'http': url, 'https': urls})
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
            self.config_option.write_config("账户1", "switch", "0").write_config("账户1", "cookies", "")
            self.initialize.info_message("请配置账户信息")
            exit()

    def get_cookie(self):
        """
        获取cookie
        :return:
        """
        url = "https://www.52pojie.cn/CSPDREL2hvbWUucGhwP21vZD10YXNrJmRvPWRyYXcmaWQ9Mg==?wzwscspd=MC4wLjAuMA=="
        response = self.session.get(url, allow_redirects=False)
        print(response.headers)

    def get_cookie1(self):
        """
        获取cookie
        :return:
        """
        url = 'https://www.52pojie.cn/home.php?mod=task&do=apply&id=2&referer=%2F'
        response = self.session.get(url, allow_redirects=False)
        print(response.headers)

    def get_task_list(self):
        """
        获取任务列表
        :return:
        """
        url = 'https://www.52pojie.cn/home.php'
        params = {
            'mod': 'task',
            'item': 'new',
        }
        response = self.session.get(url, params=params, allow_redirects=False)
        r_data = BeautifulSoup(response.text, "html.parser")
        # r_data.find('p',class="emp")
        task_list = r_data.find("div", id="ct").find("p").text
        print(task_list)

    def sign(self):
        url = 'https://www.52pojie.cn/home.php?mod=task&do=draw&id=2'
        r = self.session.get(url)
        r_data = BeautifulSoup(r.text, "html.parser")
        print(r_data)
        jx_data = r_data.find("div", id="messagetext").find("p").text
        if "您需要先登录才能继续本操作" in jx_data:
            self.initialize.error_message(f"账号Cookie 失效", is_flag=True)
        elif "恭喜" in jx_data:
            self.initialize.info_message(f"账号签到成功", is_flag=True)
        elif "不是进行中的任务" in jx_data:
            self.initialize.info_message(f"账号今日已签到", is_flag=True)
        else:
            self.initialize.error_message(f"账号签到失败", is_flag=True)

    def run(self):
        self.initialize.info_message("吾爱破解签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                self.get_account_info()
                # self.get_cookie()
                # time.sleep(1)
                # self.get_cookie1()
                # time.sleep(1)
                # self.get_task_list()
                # time.sleep(1)
                # self.sign()
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("吾爱破解签到结束")
        self.initialize.send_notify("吾爱破解")

    def get_account_info(self):
        params = {
            'mod': 'spacecp',
            'ac': 'credit',
            'showcredit': '1',
        }
        response = self.session.get('https://www.52pojie.cn/home.php', params=params)
        tree = html.fromstring(response.text)
        ul = tree.xpath('//ul[contains(@class, "creditl") and contains(@class, "bbda")]')
        if ul:
            ul = ul[0]
            msg = "账号信息：\n"
            f_str = 'li/em[normalize-space()="{0}:"]/following-sibling::text()[1]'
            msg += "吾爱币:{0:10s}\t".format(ul.xpath(f_str.format('吾爱币'))[0].strip())
            msg += "威望值:{0:10s}\t".format(ul.xpath(f_str.format('威望'))[0].strip())
            msg += "贡献值:{0:10s}\t".format(ul.xpath(f_str.format('贡献值'))[0].strip())
            msg += "悬赏值:{0:10s}\n".format(ul.xpath(f_str.format('悬赏值'))[0].strip())
            msg += "采纳率:{0:10s}\t".format(ul.xpath(f_str.format('采纳率'))[0].strip())
            msg += "热心值:{0:10s}\t".format(ul.xpath(f_str.format('热心值'))[0].strip())
            msg += "违规值:{0:10s}\t".format(ul.xpath(f_str.format('违规'))[0].strip())
            msg += "积分点:{0:10s}\t".format(ul.xpath(f_str.format('积分'))[0].strip())
            self.initialize.info_message(msg, is_flag=True)
        else:
            self.initialize.error_message("获取账号信息失败", is_flag=True)


if __name__ == '__main__':
    Template().run()
