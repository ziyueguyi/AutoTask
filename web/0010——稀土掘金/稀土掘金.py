# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :稀土掘金.py
# @作者名称 :sxzhang1
# @日期时间 : 2025/5/19 17:49
# @文件介绍 :网页登录稀土掘金账号，只需要cookies的sessionid和任意请求的params参数即可：{"aid": "","uuid":"","spider":"0","msToken":"","a_bogus":""}
const $ = new Env('稀土掘金')
cron: 22 6 * * *
"""
import json
import random
import re
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
            self.initialize.info_message("请配置账户信息")
            exit()

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
        time.sleep(1)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"签到成功", is_flag=True)
            self.initialize.info_message(f"获得矿石：{response.json()['data']['incr_point']}颗", is_flag=True)
            return True
        elif response.status_code == 200 and response.json()["err_no"] == 15001:
            self.initialize.info_message("今日已签到", is_flag=True)
            self.initialize.info_message(f"获得矿石：-颗", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
        return False

    def get_ore_num(self, params):
        response = self.session.get("https://api.juejin.cn/growth_api/v1/get_cur_point", params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"矿石总量：{response.json()['data']}颗", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def get_sign_day(self, params):
        response = self.session.get("https://api.juejin.cn/growth_api/v1/get_counts", params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"连续签到：{response.json()['data']['cont_count']}天", is_flag=True)
            self.initialize.info_message(f"累计签到：{response.json()['data']['sum_count']}天", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def draw(self, params):
        """
        每天抽奖
        :param params:
        :return:
        """
        response = self.session.post("https://api.juejin.cn/growth_api/v1/lottery/draw", json={}, params=params)
        if response.status_code == 200 and response.json()["err_no"] == 0:
            self.initialize.info_message(f"抽奖所得：{response.json()['data']['lottery_name']}", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")

    def get_article_list(self, params):
        """
        获取文章列表并进行点赞
        :param params:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            "id_type": 2,
            "sort_type": 200,
            "cate_id": "6809637769959178254",
            "cursor": "0",
            "limit": 20
        }
        url = "https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed"
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == "success":
            data = response.json()["data"]
            data = list(filter(lambda x: x['item_info'].get('article_info', {}).get('comment_count', 0) > 1, data))
            article_list = map(lambda x: x['item_info'].get('article_info', {}), random.choices(data, k=2))
            c_num = c_num_c = num_c = num = 0

            for al in article_list:
                self.initialize.info_message(f"开始点赞并收藏文章：{al['title']}({al['article_id']})")
                article_flag = self.like_article(params, al['article_id'])
                if article_flag:
                    num += 1
                    time.sleep(random.randint(3, 5))
                    num_c += self.cancel_article(params, al['article_id'])
                time.sleep(random.randint(3, 5))
                collect_id = self.get_favorites(params, al['article_id'])
                time.sleep(random.randint(1, 2))
                if collect_id and self.collect_article(params, al['article_id'], collect_id):
                    c_num += 1
                    time.sleep(random.randint(3, 5))
                    c_num_c += self.cal_collect_article(params, al['article_id'])
            self.initialize.info_message(f"文章数量：2，点赞成功数量：{num}，取消数量：{num_c}", is_flag=True)
            self.initialize.info_message(f"文章数量：2，收藏成功数量：{c_num}，取消数量：{c_num_c}", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
        time.sleep(random.randint(2, 5))

    def like_article(self, params, item_id):
        """
        点赞文章
        :param params:
        :param item_id:
        :return:
        """
        json_data = {
            'item_id': item_id,
            'item_type': 2,
            'client_type': 2608,
        }
        url = 'https://api.juejin.cn/interact_api/v1/digg/save'
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"点赞文章成功")
            return True
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
            return False

    def collect_article(self, params, article_id, collect_id):
        """
        收藏文章到收藏夹
        :param params:
        :param article_id:
        :param collect_id:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            'article_id': article_id,
            'select_collection_ids': [
                collect_id,
            ],
            'unselect_collection_ids': [],
            'is_collect_fast': False,
        }
        url = 'https://api.juejin.cn/interact_api/v2/collectionset/add_article'
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"收藏文章成功")
            return True
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
            return False

    def get_favorites(self, params, article_id):
        """
        获取收藏夹
        :param params:
        :param article_id:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }
        url = 'https://api.juejin.cn/interact_api/v2/collectionset/list'
        json_data = {
            "limit": 10,
            "cursor": "0",
            "article_id": article_id
        }
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            data = list(filter(lambda x: x['is_default'], response.json()["data"]))
            if len(data) > 0:
                self.initialize.info_message(f"收藏夹名称：{data[0]['collection_name']}")
                return data[0]['collection_id']
            else:
                self.initialize.info_message(f"没有收藏夹")
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
        return False

    def cal_collect_article(self, params, article_id):
        """
        取消收藏文章
        :param params:
        :param article_id:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }
        json_data = {
            "article_id": article_id
        }
        url = 'https://api.juejin.cn/interact_api/v2/collectionset/delete_article'
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"取消收藏成功")
            return 1
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
            return 0

    def cancel_article(self, params, item_id):
        """
        取消点赞
        :param params:
        :param item_id:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            'item_id': item_id,
            'item_type': 2,
            'client_type': 2608,
        }
        url = 'https://api.juejin.cn/interact_api/v1/digg/cancel'
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"取消点赞成功")
            return 1
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
            return 0

    def like_boiling_point(self, params, item_id):
        """
        点赞沸点
        :param params:
        :param item_id:
        :return:
        """
        json_data = {
            "item_id": item_id,
            "item_type": 4,
            "client_type": 2608
        }
        url = 'https://api.juejin.cn/interact_api/v1/digg/save'
        response = self.session.post(url, params=params, json=json_data)
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"点赞成功")
            return True
        else:
            self.initialize.error_message(f"点赞沸点失败", is_flag=True)
            self.initialize.error_message(f"未知错误:{response.text}")
            return False

    def cancel_boiling_point(self, params, item_id):
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            "item_id": item_id,
            "item_type": 4,
            "client_type": 2608
        }
        url = 'https://api.juejin.cn/interact_api/v1/digg/cancel'
        response = self.session.post(url, params=params, json=json_data)
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"取消点赞成功")
            return 1
        else:
            self.initialize.error_message(f"未知错误:{response.text}")
            return 0

    def get_hot_boiling_point(self, params):
        """
        获得沸点并点赞
        :param params:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            'id_type': 4,
            'sort_type': 200,
            'cursor': '0',
            'limit': 20,
        }
        url = 'https://api.juejin.cn/recommend_api/v1/short_msg/hot'
        response = self.session.post(url, params=params, json=json_data, )
        if response.status_code == 200 and response.json()["err_msg"] == "success":
            data = response.json()["data"]
            boiling_point_list = filter(lambda x: not x['author_user_info']['isfollowed'], random.choices(data, k=2))
            f_num = f_num_c = num_c = num = 0
            for ppl in boiling_point_list:
                time.sleep(random.randint(3, 5))
                self.initialize.info_message(f"点赞沸点：{ppl['msg_Info']['content']}")
                if self.like_boiling_point(params, ppl['msg_id']):
                    time.sleep(random.randint(3, 5))
                    num_c += self.cancel_boiling_point(params, ppl['msg_id'])
                    num += 1
                self.initialize.info_message(f"关注掘友：{ppl['author_user_info']['user_name']}")
                time.sleep(random.randint(3, 5))
                if self.follow_digging_friends(params, ppl['author_user_info']['user_id']):
                    time.sleep(random.randint(3, 5))
                    f_num_c += self.cal_follow_digging_friends(params, ppl['author_user_info']['user_id'])
                    f_num += 1
            self.initialize.info_message(f"沸点数量：2，点赞成功数量：{num}，取消成功：{num_c}", is_flag=True)
            self.initialize.info_message(f"关注作者：2，关注成功数量：{f_num}，取消成功：{f_num_c}", is_flag=True)
        else:
            self.initialize.error_message(f"未知错误:{response.text}", is_flag=True)
        time.sleep(random.randint(2, 5))

    def follow_digging_friends(self, params, msg_id):
        """
        关注掘友
        :param params:
        :param msg_id:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            'id': '641770521633085',
            'type': 1,
        }
        url = 'https://api.juejin.cn/interact_api/v1/follow/do'
        response = self.session.post(url, params=params, json=json_data)
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"关注成功")
            return True
        else:
            self.initialize.error_message(f"关注失败：{response.text}")
        return False

    def send_boiling_point(self, params):
        """
        发送沸点
        :param params:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }
        num = 0
        for i in range(2):
            num = 0
            while True:
                num += 1
                one = self.initialize.notify.Notify().one()
                time.sleep(1)
                if re.search(r'[党国政贪腐黄赌毒枪杀淫乱]', one):
                    continue
                elif num > 5:
                    self.initialize.error_message(f"请勿发送敏感词", is_flag=True)
                else:
                    json_data = {
                        'content': f'[7210002980895916043#挑战每日一条沸点#] {one}',
                        'mentions': [],
                        'sync_to_org': False,
                        'theme_id': '7210002980895916043',
                    }
                    url = 'https://api.juejin.cn/content_api/v1/short_msg/publish'
                    response = self.session.post(url, params=params, json=json_data)
                    if response.status_code == 200 and response.json()["err_msg"] == 'success':
                        self.initialize.info_message(f"每日一言：{one}({response.json().get('msg_id')})", is_flag=True)
                    else:
                        self.initialize.error_message(f"发送失败：{response.text}")
                    break
        self.initialize.info_message(f"发布沸点：2，发布成功：{num}，发布失败{2 - num}", is_flag=True)
        time.sleep(1)

    def cal_follow_digging_friends(self, params, msg_id):
        """
        取消关注的掘友
        :param msg_id:
        :param params:
        :return:
        """
        params = {
            'aid': params.get("aid"),
            'uuid': params.get("uuid"),
            'spider': params.get("spider"),
        }

        json_data = {
            'id': '641770521633085',
            'type': 1,
        }
        url = 'https://api.juejin.cn/interact_api/v1/follow/undo'
        response = self.session.post(url, params=params, json=json_data)
        if response.status_code == 200 and response.json()["err_msg"] == 'success':
            self.initialize.info_message(f"取消关注成功")
            return 1
        else:
            self.initialize.error_message(f"取消关注失败：{response.text}")
        return 0

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
                    self.get_article_list(params)
                    self.get_hot_boiling_point(params)
                    self.send_boiling_point(params)
                    if self.sign_in(params):
                        self.draw(params)
                    time.sleep(1)
                    self.get_ore_num(params)
                    time.sleep(1)
                    self.get_sign_day(params)
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("稀土掘金签到结束")
        self.initialize.send_notify("稀土掘金")


if __name__ == '__main__':
    # Template().run()
    one = Template().initialize.notify.Notify().one()
    print(one)
