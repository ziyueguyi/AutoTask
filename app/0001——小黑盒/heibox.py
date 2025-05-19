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
import importlib.util
import logging
import random
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
        self.init_config()

    def get_nonce_str(self, length: int = 32) -> str:
        """
        生成随机字符串
        参数:
            length: 密钥参数
        返回:
            str: 随机字符串
        """
        source = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        result = "".join(random.choice(source) for _ in range(length))
        return result

    def hkey(self, key):
        params = {"urlpath": key, "nonce": self.n, "timestamp": self.t}
        zz = requests.get("http://146.56.234.178:8077/encode", params=params).text
        return zz

    def params(self, key,cookie):
        p = {
            "_time": self.t,
            "hkey": self.hkey(key),
            "nonce": self.n,
            "imei": self.user['imei'],
            "heybox_id": self.user['heybox_id'],
            "version": self.user['version'],
            "divice_info": "M2012K11AC",
            "x_app": "heybox",
            "channel": "heybox_xiaomi",
            "os_version": "13",
            "os_type": "Android"
        }
        return p

    def head(self,cookie):
        head = {
            "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 ApiMaxJia/1.0",
            "cookie": cookie,
            "Referer": "http://api.maxjia.com/"
        }
        return head

    def b64encode(self, data: str) -> str:
        result = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return str(result)

    def getpost(self,cookie):
        req = requests.get(
            url="https://api.xiaoheihe.cn/bbs/app/feeds/news",
            params=self.params("/bbs/app/feeds/news"),
            headers=self.head(cookie)
        ).json()['result']['links'][1]['linkid']

        def click(link_id):
            head = self.params("/bbs/app/link/share/click")
            head['h_src'] = self.b64encode('news_feeds_-1')
            head['link_id'] = link_id
            head['index'] = 1
            req = requests.get(url="https://api.xiaoheihe.cn/bbs/app/link/share/click", params=head,
                               headers=self.head()).json()['status']
            if req == "ok":
                logging.info("分享成功")
                msg_req = "分享成功"
                message.append(f"😊分享成功")
            else:
                logging.info("分享失败")
                msg_req = "分享失败"
                message.append(f"😢分享失败")
            return msg_req

        def check():
            head = self.params("/task/shared/")
            head['h_src'] = self.b64encode('news_feeds_-1')
            head['shared_type'] = 'normal'
            req = requests.get(url="https://api.xiaoheihe.cn/task/shared/", params=head, headers=self.head()).json()[
                'status']
            if req == "ok":
                logging.info("检查分享成功")
                msg_req = "检查分享成功"
            else:
                logging.info("检查分享失败")
                msg_req = "检查分享失败"
            return msg_req

        return click(req) + "\n" + check()

    def heibox_sgin(self, user):
        cookie = self.config_option.read_config_key(user, 'cookies')
        if cookie != "":
            try:
                req = requests.get(url="https://api.xiaoheihe.cn/task/sign/", params=self.params("/task/sign/"),
                                   headers=self.head()).json()
                fx = self.getpost(cookie)
                if req['status'] == "ok":
                    if req['msg'] == "":
                        logging.info("小黑盒:已经签到过了")
                        message.append(f"😢{self.user['heybox_id']},小黑盒:已经签到过了")
                        return fx + "\n已经签到过了"
                    else:
                        logging.info(f"小黑盒:{req['msg']}")
                        message.append(f"😊{self.user['heybox_id']},小黑盒:{req['msg']}")
                        return f"{fx}\n{req['msg']}"
                else:
                    logging.info(f"小黑盒:签到失败 - {req['msg']}")
                    message.append(f"😢小黑盒:签到失败 - {req['msg']}")
                    return f"{fx}\n签到失败 - {req['msg']}"
            except Exception as e:
                logging.info(f"小黑盒:出现了错误,错误信息{e}")
                message.append(f"😢小黑盒:出现了错误,错误信息{e}")
                return f"出现了错误,错误信息{e}"
        else:
            logging.info("小黑盒:没有配置cookie")
            message.append(f"😢小黑盒:没有配置cookie")
            return "没有配置cookie"

    def init_config(self):
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")

    def run(self):
        self.initialize.init()  # 初始化日志系统
        # 判断是否存在文件
        sections = self.config_option.read_config_key()
        for index, section in enumerate(sections):
            if not self.config_option.read_config_key(section, 'switch', field_type=bool):
                self.initialize.error_message(f'😢第{index + 1}个 switch值为False，不进行任务，跳过该账号')
            else:
                self.heibox_sgin(section)
            self.initialize.message("\n")
        self.initialize.send_notify("小黑盒")  # 发送通知


if __name__ == '__main__':
    XiaoHeiHe().run()
