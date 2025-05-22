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

from bs4 import BeautifulSoup
from lxml import html

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
            self.session.cookies.update({
                'wzws_sessionid': 'oGgtY5eBMzNkMGYygDYwLjE5MC4yNTMuNTiCZGIxY2Fh',
                'Hm_lvt_46d556462595ed05e05f009cdafff31a': '1745834615,1747805081',
                'HMACCOUNT': 'E0411248A37880DB',
                'wzws_sid': 'a114e8514383f6844246a86c3db046f896354f6694e194ea55d07cba7596794bbb5f2e0b32c580af39a61e0d3c6512921911e43422e36ada90e83f4fe0100f58f8a3422bb6c2d429abbc60a8b28be60c6f5032834aed9abed3b9f96cefed104f543470583c5b2b34742ec1e672ec96c9',
                'htVC_2132_saltkey': 'Ndif1oDp',
                'htVC_2132_lastvisit': '1747802125',
                'htVC_2132_seccodecSAm7L': '2552298.5c6aad293b179bc643',
                'htVC_2132_seccodecSAm7LSlO': '2552299.796a85b9cf3ce8b19d',
                'htVC_2132_ulastactivity': '1747805816%7C0',
                'htVC_2132_auth': '9f4fBrBqCgO1%2FuCpW2o%2BkcjEq2%2BAJFmOYfbY4jBA%2BKxnKiWqFCc1x%2FCFyMP73%2F1aH6KqZNODckb7XRSL85P7ZHF33xWh',
                'htVC_2132_resendemail': '1747805816',
                'htVC_2132_sid': '0',
                'htVC_2132_nofavfid': '1',
                'htVC_2132_noticonf': '2400245D1D3_3_1',
                'htVC_2132_con_request_uri': 'https%3A%2F%2Fwww.52pojie.cn%2Fconnect.php%3Fmod%3Dlogin%26op%3Dcallback%26referer%3Dindex.php',
                'htVC_2132_client_created': '1747805950',
                'htVC_2132_client_token': '8E279D62E1C008747788E62B5E2CF068',
                'htVC_2132_connect_js_name': 'user_bind',
                'htVC_2132_connect_js_params': 'YToxOntzOjQ6InR5cGUiO3M6OToibG9naW5iaW5kIjt9',
                'htVC_2132_connect_login': '1',
                'htVC_2132_connect_is_bind': '1',
                'htVC_2132_connect_uin': '8E279D62E1C008747788E62B5E2CF068',
                'htVC_2132_stats_qc_reg': '3',
                'htVC_2132_home_diymode': '1',
                'htVC_2132_st_p': '2400245%7C1747806002%7C0872bfce25ad2a8cccb7b0bb2a7f7098',
                'htVC_2132_viewid': 'tid_17688',
                'htVC_2132_st_t': '2400245%7C1747806346%7C070b247afc5c270cf480a41fa650b956',
                'htVC_2132_atarget': '1',
                'htVC_2132_forum_lastvisit': 'D_8_1747806346',
                'htVC_2132_visitedfid': '8D25',
                'htVC_2132_seccodecSAY0z0': '2554953.0823f57fd7c3601ac8',
                'htVC_2132_checkpm': '1',
                'htVC_2132_lastcheckfeed': '2400245%7C1747806513',
                'htVC_2132_lastact': '1747806523%09home.php%09space',
                'Hm_lpvt_46d556462595ed05e05f009cdafff31a': '1747806527',
            }
            )
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
            msg += f"吾爱币:{ul.xpath('li/em[normalize-space()="吾爱币:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"威望值:{ul.xpath('li/em[normalize-space()="威望:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"贡献值:{ul.xpath('li/em[normalize-space()="贡献值:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"悬赏值:{ul.xpath('li/em[normalize-space()="悬赏值:"]/following-sibling::text()[1]')[0].strip():10s}\n"
            msg += f"采纳率:{ul.xpath('li/em[normalize-space()="采纳率:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"热心值:{ul.xpath('li/em[normalize-space()="热心值:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"违规值:{ul.xpath('li/em[normalize-space()="违规:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            msg += f"积分点:{ul.xpath('li/em[normalize-space()="积分:"]/following-sibling::text()[1]')[0].strip():10s}\t"
            self.initialize.info_message(msg,  is_flag=True)
        else:
            self.initialize.error_message("获取账号信息失败", is_flag=True)


if __name__ == '__main__':
    Template().run()
