# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :网页登录百度贴吧账号，只需要cookies的BDUSS和STOKEN即可：{"BDUSS":"","STOKEN":""}
# 青龙环境变量 TIEBA_COOKIE，多账号用 & 或换行分隔
# 示例：{"BDUSS":"账号1","STOKEN":"xxx"}&{"BDUSS":"账号2","STOKEN":"yyy"}
new Env('百度贴吧');
cron: 20 6 * * *
"""
import hashlib
import random
import time
from importlib import util
from pathlib import Path
from urllib.parse import unquote

from curl_cffi import requests
from fake_useragent import UserAgent  # pip install fake-useragent
from lxml import html


class PostBar:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / 'public'
        import_set_spc = util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        self.import_set = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.initialize = self.import_set.import_initialize()
        account_loader_spc = util.spec_from_file_location(
            'account_loader', str(tools_path / 'tools' / 'account_loader.py')
        )
        account_loader = util.module_from_spec(account_loader_spc)
        account_loader_spc.loader.exec_module(account_loader)
        self.load_accounts = account_loader.load_accounts
        self.env_name = 'BAIDU_COOKIE'
        self.session = requests.Session(timeout=10)
        self.session.headers.update({
            'connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'tieba.baidu.com',
            'charset': 'UTF-8',
            'User-Agent': UserAgent().chrome,
        })

    def get_tbs(self):
        """验证账号有效性，返回 tbs。"""
        try:
            response = self.session.get('https://tieba.baidu.com/dc/common/tbs')
            data = response.json()
            if data.get('is_login') == 1:
                return data.get('tbs')
            self.initialize.error_message("账号未登录或 Cookie 失效", is_flag=True)
            return None
        except Exception as e:
            self.initialize.error_message(e.__str__(), is_flag=True)
            return None

    def get_follow_bar(self):
        """获取已关注的贴吧名称列表。"""
        try:
            response = self.session.get('https://tieba.baidu.com/mo/q/newmoindex')
            if response.status_code != 200:
                self.initialize.error_message("获取贴吧失败", is_flag=True)
                return []
            forums = response.json().get('data', {}).get('like_forum') or []
            bar_list = [item['forum_name'] for item in forums if item.get('forum_name')]
            self.initialize.info_message(f"总计关注 {len(bar_list)} 个贴吧", is_flag=True)
            return bar_list
        except Exception as e:
            self.initialize.error_message(e.__str__(), is_flag=True)
            return []

    def sign_bar(self, bar_list, tbs):
        """逐吧签到，返回 {贴吧名: 状态文案}。"""
        tie_info = {}
        for index, bar_name in enumerate(bar_list, 1):
            data = {
                'kw': bar_name,
                'tbs': tbs,
                'sign': hashlib.md5(f'kw={bar_name}tbs={tbs}tiebaclient!!!'.encode('utf-8')).hexdigest(),
            }
            try:
                response = self.session.post('http://c.tieba.baidu.com/c/c/forum/sign', data=data)
                if response.status_code != 200:
                    tie_info[bar_name] = "签到状态：签到失败"
                else:
                    error_code = str(response.json().get('error_code', ''))
                    if error_code == '0':
                        tie_info[bar_name] = "签到状态：签到成功"
                    elif error_code == '160002':
                        tie_info[bar_name] = "签到状态：重复签到"
                    else:
                        tie_info[bar_name] = f"签到状态：未知错误({error_code})"
                        self.initialize.info_message(f"【{bar_name}】未知错误: {response.text}")
            except Exception as e:
                tie_info[bar_name] = f"签到状态：异常({e})"
            if index < len(bar_list):
                time.sleep(random.uniform(0.5, 1.5))
        return tie_info

    def get_status(self, tie_info):
        """输出关注贴吧的签到结果与等级信息。"""
        params = {'v': int(time.time() * 1000)}
        response = self.session.get('https://tieba.baidu.com/f/like/mylike', params=params)
        if response.status_code != 200:
            self.initialize.error_message("获取贴吧状态失败", is_flag=True)
            return

        tree = html.fromstring(response.text)
        rows = tree.xpath('//div[@class="forum_table"]/table//tr[not(./th)]')
        reported = set()
        for row in rows:
            bar_name = (row.xpath('.//a[@title]/text()') or [None])[0]
            if not bar_name:
                continue
            bar_name = unquote(bar_name)
            exp = (row.xpath('.//a[@class="cur_exp"]/text()') or ['-'])[0]
            badge_title = (row.xpath('.//div[@class="like_badge_title"]/text()') or ['-'])[0]
            badge_level = (row.xpath('.//div[@class="like_badge_lv"]/text()') or ['-'])[0]
            status = tie_info.get(bar_name, "签到状态：未匹配到签到结果")
            self.initialize.info_message(f"贴吧名称：【{bar_name}】", is_flag=True)
            self.initialize.info_message(status, is_flag=True)
            self.initialize.info_message(f"贴吧经验：{exp}", is_flag=True)
            self.initialize.info_message(f"等级称号：{badge_title}", is_flag=True)
            self.initialize.info_message(f"数字等级：{badge_level}", is_flag=True)
            self.initialize.info_message("*" * 25, is_flag=True)
            reported.add(bar_name)

        for bar_name, status in tie_info.items():
            if bar_name not in reported:
                self.initialize.info_message(f"贴吧名称：【{bar_name}】", is_flag=True)
                self.initialize.info_message(status, is_flag=True)
                self.initialize.info_message("*" * 25, is_flag=True)

    def run(self):
        self.initialize.info_message("贴吧签到开始")
        accounts = self.load_accounts(self.env_name)
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            self.initialize.send_notify("贴吧")
            return
        for ind, (name, cookies) in enumerate(accounts):
            self.initialize.info_message(f"共{len(accounts)}个账户，第{ind + 1}个账户：{name}")
            self.session.cookies.clear()
            self.session.cookies.update(cookies)
            try:
                tbs = self.get_tbs()
                if not tbs:
                    continue
                time.sleep(random.uniform(1, 2))
                bar_list = self.get_follow_bar()
                if not bar_list:
                    self.initialize.error_message("未获取到关注贴吧", is_flag=True)
                    continue
                tie_info = self.sign_bar(bar_list, tbs)
                self.get_status(tie_info)
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("贴吧签到结束")
        self.initialize.send_notify("贴吧")


if __name__ == '__main__':
    PostBar().run()
