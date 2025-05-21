#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: 小黑盒.py
Author: WFRobert
Date: 2023/5/19 10:32
cron: 0 15 6 * * ?
new Env('小黑盒签到脚本');
Description: 小黑盒脚本,实现每日自动完成小黑盒任务
Update: 2023/9/1 更新cron
"""
import base64
import copy
import importlib.util
import json
import logging
import random
import time
from pathlib import Path

import requests

# 通知内容
message = []


# 小黑盒签到
class XiaoHeiHe:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / 'public'
        import_set_spc = importlib.util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        self.import_set = importlib.util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.notify = self.import_set.import_notify()
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 ApiMaxJia/1.0",
            "Referer": "http://api.maxjia.com/"
        })
        self.init_config()

    @staticmethod
    def get_nonce_str(length: int = 32) -> str:
        """
        生成随机字符串
        :param length: 密钥参数
        :return:
        """
        source = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        result = "".join(random.choice(source) for _ in range(length))
        return result

    @staticmethod
    def hkey(key, t, n):
        params = {"urlpath": key, "nonce": n, "timestamp": t}
        zz = requests.get("http://146.56.234.178:8077/encode", params=params).text
        return zz



    @staticmethod
    def b64encode(data: str) -> str:
        result = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return str(result)

    def sign(self, params, t, n):
        """
        签到程序
        :param n:
        :param t:
        :param params:
        :return:
        """
        url = "https://api.xiaoheihe.cn/task/sign/"
        params['hkey'] = self.hkey("/task/sign/", t, n)
        response = self.session.get(url, params=params)
        print(response.json())

    def get_article(self, params, t, n):
        params['hkey'] = self.hkey("/bbs/app/feeds/news", t, n)
        url = "https://api.xiaoheihe.cn/bbs/app/feeds/news"
        response = self.session.get(url, params=params)
        if response.json()['status'] == "ok":
            return response.json()['result']['links'][1]['linkid']
        else:
            return None

    def click_article(self, params, article_id, t, n):
        params = copy.deepcopy(params)
        params['h_src'] = self.b64encode('news_feeds_-1')
        params['link_id'] = article_id
        params['index'] = 1
        params['hkey'] = self.hkey("/bbs/app/link/share/click", t, n)
        url = "https://api.xiaoheihe.cn/bbs/app/link/share/click"
        response = self.session.get(url, params=params)
        print(response.json())

    def share_article(self, params, t, n):
        params = copy.deepcopy(params)
        params['h_src'] = self.b64encode('news_feeds_-1')
        params['shared_type'] = 'normal'
        url = "https://api.xiaoheihe.cn/task/shared/"
        params['hkey'] = self.hkey("/task/shared/", t, n)
        response = self.session.get(url, params=params)
        print(response.json())

    def init_config(self):
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")
            self.config_option.write_config("账户1", "params", "")

    def run(self):
        # 判断是否存在文件
        sections = self.config_option.read_config_key()
        for index, section in enumerate(sections):
            if self.config_option.read_config_key(section, 'switch', field_type=bool):
                self.session.headers.update({'cookies': self.config_option.read_config_key(section, 'cookies')})
                params = json.loads(self.config_option.read_config_key(section, 'params'))
                t = str(int(time.time()))
                n = self.get_nonce_str()
                params.update({
                    "_time": t,
                    "nonce": n,
                    "divice_info": "M2012K11AC",
                    "x_app": "heybox",
                    "channel": "heybox_huawei",
                    "os_version": "13",
                    "os_type": "Android"
                })
                self.sign(params, t, n)
                time.sleep(1)
                article_id = self.get_article(params, t, n)
                time.sleep(1)
                if article_id:
                    self.click_article(params, article_id, t, n)
                    self.share_article(params, t, n)
                # self.hei_box_sign(section)
            else:
                self.initialize.error_message(f'😢第{index + 1}个 switch值为False，不进行任务，跳过该账号')
            self.initialize.message("\n")
        self.initialize.send_notify("小黑盒")  # 发送通知


if __name__ == '__main__':
    XiaoHeiHe().run()
