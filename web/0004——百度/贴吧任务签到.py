# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :贴吧任务签到.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 17:11
# @文件介绍 :网页登录百度贴吧账号，只需要cookies的BDUSS和CUID即可：{"BDUSS":"","CUID":""}
# 青龙环境变量 TIEBA_TASK_COOKIE，多账号用 & 或换行分隔
# 示例：{"BDUSS":"账号1","CUID":"xxx"}&{"BDUSS":"账号2","CUID":"yyy"}
new Env('贴吧任务签到')
cron: 19 6 * * *
"""

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
        self.baseUrl = 'https://tieba.baidu.com'

    def get_user_info(self):
        user_url = f'{self.baseUrl}/mo/q/usergrowth/showUserGrowth?client_type=2&client_version=12.60.1.2'
        response = self.session.get(user_url)
        if response.status_code == 200 and response.json():
            data = response.json().get('data') or {}
            user = data.get('user') or {}
            user_name = user.get('uname')
            tbs = data.get('tbs')
            if not user_name or not tbs:
                self.initialize.error_message("获取用户信息失败：返回数据不完整", is_flag=True)
                return None, None
            self.initialize.info_message(f"昵称：{user_name}", is_flag=True)
            return user_name, tbs
        self.initialize.error_message("获取用户信息失败", is_flag=True)
        return None, None

    def sign(self, tbs, user_name, cookies):
        """账号进行成长体系签到。"""
        cuid = cookies.get("CUID")
        if not cuid:
            self.initialize.error_message(f"{user_name}签到失败：缺少 CUID", is_flag=True)
            return
        params = {
            'tbs': tbs,
            'act_type': 'page_sign',
            'cuid': cuid,
            'client_type': 2,
            'brand': 'OPPO',
            'model': 'OPPO%20R9s',
            'zid': '',
            'clientVersion': '12.60.1.2',
            'clientType': '2',
        }
        url = f'{self.baseUrl}/mo/q/usergrowth/commitUGTaskInfo'
        response = self.session.post(url, params=params)
        if response.status_code == 200 and response.json().get("no") == 0:
            self.initialize.info_message(f"{user_name}签到成功", is_flag=True)
        else:
            self.initialize.error_message(f"{user_name}签到失败：{response.text}", is_flag=True)

    def get_point(self):
        """获取账号积分信息。"""
        url = f'{self.baseUrl}/mo/q/usergrowth/showUserGrowth?client_type=2&client_version=12.60.1.2'
        response = self.session.get(url)
        if response.status_code == 200 and response.json().get("no") == 0:
            data = response.json()['data']
            level_list = [x for x in data.get('level_info', []) if x.get('is_current') == 1]
            if not level_list:
                self.initialize.error_message("获取等级信息失败", is_flag=True)
                return
            level = level_list[0]
            points = level['next_level_value'] - level['growth_value']
            self.initialize.info_message(f"当前账号等级：{level['level']}", is_flag=True)
            self.initialize.info_message(f"当前贴贝余额：{data['tmoney']['current']}", is_flag=True)
            self.initialize.info_message(f"当前已有积分：{data['growth_info']['value']}", is_flag=True)
            self.initialize.info_message(f"下级所需积分：{points}", is_flag=True)
        else:
            self.initialize.error_message("获取积分失败", is_flag=True)

    def run(self):
        self.initialize.info_message("贴吧任务签到开始")
        accounts = self.load_accounts(self.env_name)
        if not accounts:
            self.initialize.error_message(f"未配置账号，请在青龙面板设置环境变量 {self.env_name}")
            self.initialize.send_notify("贴吧签到")
            return
        for ind, (name, cookies) in enumerate(accounts):
            self.initialize.info_message(f"共{len(accounts)}个账户，第{ind + 1}个账户：{name}")
            self.session.cookies.clear()
            self.session.cookies.update(cookies)
            try:
                user_name, tbs = self.get_user_info()
                if not user_name:
                    continue
                time.sleep(1)
                self.sign(tbs, user_name, cookies)
                time.sleep(1)
                self.get_point()
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("贴吧任务签到结束")
        self.initialize.send_notify("贴吧签到")


if __name__ == '__main__':
    PostBar().run()
