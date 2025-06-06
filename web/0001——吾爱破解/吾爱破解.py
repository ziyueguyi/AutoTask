#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :吾爱破解.py
# @作者名称 :sxzhang1
# @任务名称：name 吾爱破解
# @任务时间：cron: 0 25 8 * * *
# @目标网站：url: https://www.52pojie.cn/home.php?mod=task&item=done
# @日期时间 : 2023/3/9 15:01
# @文件介绍 :52pojie自动签到,实现每日自动签到52pojie,获取cookie中htVC_2132_saltkey和htVC_2132_auth即可，
"""
import json
import os
import random
import re
import time
from importlib import util
from pathlib import Path

import execjs
from curl_cffi import requests
from lxml import html


class Template:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / 'public'
        import_set_spc = util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        self.import_set = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session(timeout=10)
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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

    def get_task_list(self):
        """
        获取任务列表
        :return:
        """
        time.sleep(random.randint(2, 5))
        url = 'https://www.52pojie.cn/home.php'
        params = {
            'mod': 'task',
            'item': 'new',
        }
        response = self.session.get(url, params=params, allow_redirects=False)
        if response.status_code == 200:
            html_xpath = html.fromstring(response.text)
            tasks = html_xpath.xpath("//*[@id='ct']//table//tr[.//a[contains(text(), '每日签到红包任务')]]")
            no_task = html_xpath.xpath("//*[@id='ct']//p[contains(text(), '暂无新任务')]/text()")
            if tasks:
                task = tasks[0]
                # 提取任务名
                task_name = task.xpath(".//a[contains(text(), '每日签到红包任务')]/text()")[0].strip()
                # 提取描述文字
                description = task.xpath(".//p[@class='xg2']/text()")
                desc_text = " ".join([d.strip() for d in description if d.strip()])
                # 提取积分信息
                reward = task.xpath(".//td[@class='xi1 bbda hm']/text()")[0].strip()
                # 提取申请链接
                apply_link = task.xpath(".//a[@href]/@href")[0]
                msg = f"任务名称：{task_name}，\n任务描述：{desc_text}，\n任务奖励：{reward}，\n任务链接：{apply_link}"
                self.initialize.info_message(msg, is_flag=True)
                return True
            elif no_task:
                self.initialize.info_message(no_task[0], is_flag=True)
            else:
                self.initialize.info_message('没有找到相关任务', is_flag=True)
        else:
            self.initialize.error_message(f"获取任务列表失败")
        return False

    def get_cookie(self):
        """
        获取加签的cookies
        :return:
        """

        params = {
            'mod': 'task',
            'item': 'new',
        }
        url = 'https://www.52pojie.cn/home.php'
        response = self.session.get(url, params=params).text
        le = re.search(r"LE='(.*?)';", response, re.S)
        lz, lj = re.search(r"LZ='(\d+)'", response), re.search(r"LJ='(\d+)'", response)
        if lz and lj and le:
            self.initialize.info_message(f"吾爱三神获取成功：\nlz:{lz.group(1)}\n lj:{lj.group(1)}\n le:{le.group(1)}")
            ctx = execjs.compile(open('env_add_salt.js', encoding='utf8').read())
            data = ctx.call('get_fp', le.group(1), lz.group(1), lj.group(1))
            time.sleep(1)
            wzws_sid_old = self.session.cookies.get("wzws_sid")
            self.session.post('https://www.52pojie.cn/waf_zw_verify', data=data)
            wzws_sid_new = self.session.cookies.get("wzws_sid")
            if wzws_sid_new != wzws_sid_old:
                self.initialize.info_message(f"wzws_sid获取成功：{wzws_sid_new}")
                return True
            else:
                self.initialize.error_message("wzws_sid更新失败")
                exit()
        else:
            self.initialize.error_message("lz,lj,le获取失败，可能cookies已失效", flag=True)
            exit()

    def sign(self):
        """
        进行签到
        :return:
        """

        params = {
            'mod': 'task',
            'do': 'apply',
            'id': '2',
        }
        time.sleep(random.randint(1, 20))
        url = 'https://www.52pojie.cn/home.php'
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            html_xpath = html.fromstring(response.text)
            rows = html_xpath.xpath("//div[@id='messagetext']/p/text()")
            if rows:
                row = rows[0]
                if "任务已完成" in row:
                    self.initialize.info_message(f"账号签到成功", is_flag=True)
                elif '本期您已申请过此任务' in row:
                    self.initialize.info_message(f"账号今日已签到", is_flag=True)
                elif "您需要先登录才能继续本操作" in row:
                    self.initialize.error_message(f"账号Cookie 失效", is_flag=True)
                else:
                    self.initialize.error_message(f"账号签到失败", is_flag=True)
                    self.initialize.info_message(response.text)
            else:
                self.initialize.error_message(f"未知错误", is_flag=True)
                self.initialize.info_message(response.text)
        else:
            self.initialize.error_message(f"获取签到结果失败")

    def get_account_info(self):
        """
        获取账户信息
        :return:
        """
        params = {
            'mod': 'spacecp',
            'ac': 'credit',
            'showcredit': '1',
        }
        time.sleep(random.randint(3, 5))
        response = self.session.get('https://www.52pojie.cn/home.php', params=params, timeout=10)
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

    def run(self):
        self.set_env()
        self.initialize.info_message("吾爱破解签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                if self.get_cookie() and self.get_task_list():
                    self.sign()
                self.get_account_info()
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("吾爱破解签到结束")
        self.initialize.send_notify("吾爱破解")

    @staticmethod
    def set_env():
        os.environ.setdefault('DD_BOT_SECRET', 'SEC999d3ff220cea418c54ab02c181b9db122f76e1db349f69e45cc507d9ca64ad0')
        os.environ.setdefault('DD_BOT_TOKEN', '49eec26b2a4532e64e47e7d90376c3b305c10328980bb3572d91e7587bb87cbd')



if __name__ == '__main__':
    Template().run()
