# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 11:04
# @文件介绍 :
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


class PostBar:
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
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")

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

    def sign_bar(self, bar_list, tbs):
        """
        贴吧签到
        :param bar_list:贴吧名称
        :param tbs:
        :return:
        """
        for bl in bar_list:
            data = {
                'kw': bl,
                'tbs': tbs,
                'sign': hashlib.md5(f'kw={bl}tbs={tbs}tiebaclient!!!'.encode('utf-8')).hexdigest()
            }
            response = self.session.post('http://c.tieba.baidu.com/c/c/forum/sign', data=data)
            if response.status_code == 200:
                if response.json()['error_code'] == '0':
                    self.initialize.info_message(f"贴吧【{bl}】签到成功", is_flag=True)
                elif response.json()['error_code'] == '160002':
                    self.initialize.info_message(f"贴吧【{bl}】已经签过到了", is_flag=True)
                else:
                    self.initialize.info_message("未知错误", is_flag=True)
            else:
                self.initialize.error_message(f"贴吧【{bl}】签到失败", is_flag=True)

    def run(self):
        self.initialize.info_message("贴吧签到开始")
        account_list = self.config_option.read_config_key()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            tbs = self.get_tbs()
            if tbs:
                time.sleep(random.randint(1, 2))
                bar_list = self.get_follow_bar()
                self.sign_bar(bar_list, tbs)
        self.initialize.info_message("贴吧签到结束")
        self.initialize.send_notify("「贴吧」")


if __name__ == '__main__':
    PostBar().run()
