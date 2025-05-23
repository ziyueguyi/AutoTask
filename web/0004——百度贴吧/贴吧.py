# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :网页登录稀土掘金账号，只需要cookies的BDUSS和CUID即可：{"BDUSS":"","CUID":""}
new Env('百度贴吧');
cron: 20 6 * * *
"""
import hashlib
import json
import random
import time
from importlib import util
from pathlib import Path
from fake_useragent import UserAgent  # pip install fake-useragent
from curl_cffi import requests
from lxml import html


class PostBar:
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
            'connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'tieba.baidu.com',
            'charset': 'UTF-8',
            'User-Agent': UserAgent().chrome,
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

    def get_tbs(self):
        """
        验证账号有效性
        """
        try:
            response = self.session.get('http://tieba.baidu.com/dc/common/tbs')
            return response.json()['tbs']
        except BaseException as e:
            self.initialize.error_message(e.__str__())
            return None

    def get_valid_bar(self, bar_name):
        """
        验证贴吧是否有效
        :param bar_name: 贴吧名称
        :return:
        """
        time.sleep(random.randint(1, 2))
        params = {'ie': 'utf-8', 'kw': bar_name, 'fr': 'search'}
        response = self.session.get(f'https://tieba.baidu.com/f', params=params)
        return response.status_code == 200 and '很抱歉，没有找到相关内容' not in response.text

    def get_follow_bar(self):
        """
        获取已关注的贴吧
        :return:
        """
        bar_list = []
        try:
            response = self.session.get('https://tieba.baidu.com/mo/q/newmoindex')
            if response.status_code == 200:
                bar_list = response.json()['data']['like_forum']
                bar_list = list(filter(lambda x: self.get_valid_bar(x['forum_name']), bar_list))
                bar_list = [data['forum_name'].replace('+', '%2B') for data in bar_list]
                self.initialize.info_message(f"总计关注{bar_list}个贴吧")
                return bar_list
            else:
                self.initialize.error_message("获取贴吧失败")
        except BaseException as e:
            self.initialize.error_message(e.__str__())
        finally:
            return bar_list

    def sign_bar(self, bar_list, tbs, tie_info):
        """
        贴吧签到
        :param bar_list:贴吧名称
        :param tbs:
        :param tie_info:
        :return:
        """
        for bl in bar_list:
            data = {
                'kw': bl,
                'tbs': tbs,
                'sign': hashlib.md5(f'kw={bl}tbs={tbs}tiebaclient!!!'.encode('utf-8')).hexdigest()
            }
            response = self.session.post('http://c.tieba.baidu.com/c/c/forum/sign', data=data)
            msg = "\n贴吧名称：【{0}】\n".format(bl)

            if response.status_code == 200:
                if response.json()['error_code'] == '0':
                    msg += "签到状态：签到成功\n"
                elif response.json()['error_code'] == '160002':
                    msg += "签到状态：重复签到\n"
                else:
                    msg += "签到状态：签到失败\n"
                    self.initialize.info_message(f"未知错误:{response.text}")
            else:
                msg += "签到状态：签到失败\n"
            msg += "贴吧经验：{0}\n".format(tie_info.get(bl, {}).get("经验值"))
            msg += "等级称号：{0}\n".format(tie_info.get(bl, {}).get("等级称号"))
            msg += "数字等级：{0}".format(tie_info.get(bl, {}).get("数字等级"))
            self.initialize.info_message(msg, is_flag=True)

    def get_status(self):
        """
        获取关注贴吧信息

        """
        params = {
            'v': int(time.time() * 1000),
        }
        response = self.session.get('https://tieba.baidu.com/f/like/mylike', params=params)
        tie_info = {}
        if response.status_code == 200:
            tree = html.fromstring(response.text)
            # 定位 tbody 下的所有 tr 行
            rows = tree.xpath('//div[@class="forum_table"]/table//tr[not(./th)]')
            for row in rows:
                bar_name = row.xpath('.//a[@title]/text()')
                exp = row.xpath('.//a[@class="cur_exp"]/text()')
                badge_title = row.xpath('.//div[@class="like_badge_title"]/text()')
                badge_level = row.xpath('.//div[@class="like_badge_lv"]/text()')
                tie_info.update({
                    bar_name[0]: {
                        "经验值": exp[0],
                        "等级称号": badge_title[0],
                        "数字等级": badge_level[0],
                    }
                })
            self.initialize.info_message("获取贴吧状态成功")
        else:
            self.initialize.error_message("获取贴吧状态失败")
        return tie_info

    def run(self):
        self.initialize.info_message("贴吧签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                tbs = self.get_tbs()
                if tbs:
                    time.sleep(random.randint(1, 2))
                    bar_list = self.get_follow_bar()
                    tie_info = self.get_status()
                    self.sign_bar(bar_list, tbs, tie_info)
            except BaseException as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("贴吧签到结束")
        self.initialize.send_notify("贴吧")


if __name__ == '__main__':
    PostBar().run()
