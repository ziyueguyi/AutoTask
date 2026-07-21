#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# @项目名称 :自动化任务
# @文件名称 :天翼网盘.py
# @作者名称 :张洛
# @日期时间 :2025/04/30 9:25
# @文件介绍 :天翼网盘脚本,实现每日自动完成天翼网盘签到
const $ = new Env('天翼网盘签到脚本')
cron: 0 10 6 * * ?
"""

import base64
import importlib.util
import json
import re
import time
from pathlib import Path

from curl_cffi import requests
import rsa

BI_RM = list("0123456789abcdefghijklmnopqrstuvwxyz")

B64MAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


# 天翼云盘
# 使用了开源项目https://www.52pojie.cn/forum.php?mod=viewthread&tid=1784111&highlight=%CC%EC%D2%ED%D4%C6%C5%CC
class TianYiYunPan:
    def __init__(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent.parent / 'public'
        import_set_spc = importlib.util.spec_from_file_location('ImportSet', str(tools_path / 'ImportSet.py'))
        self.import_set = importlib.util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(self.import_set)
        self.import_set = self.import_set.ImportSet()
        self.initialize = self.import_set.import_initialize()
        self.config_option = self.import_set.import_config_option()
        self.session = requests.Session(timeout=10)
        self.session.headers.update({
            # "Accept": "*/*",
            # "Accept-Encoding": "gzip, deflate, br, zstd",
            # "Content-type": "application/json",
            # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        })
        self.init_config()

    def int2char(self, a):
        return BI_RM[a]

    def b64tohex(self, a):
        d = ""
        e = 0
        c = 0
        for i in range(len(a)):
            if list(a)[i] != "=":
                v = B64MAP.index(list(a)[i])
                if 0 == e:
                    e = 1
                    d += self.int2char(v >> 2)
                    c = 3 & v
                elif 1 == e:
                    e = 2
                    d += self.int2char(c << 2 | v >> 4)
                    c = 15 & v
                elif 2 == e:
                    e = 3
                    d += self.int2char(c)
                    d += self.int2char(v >> 2)
                    c = 3 & v
                else:
                    e = 0
                    d += self.int2char(c << 2 | v >> 4)
                    d += self.int2char(15 & v)
        if e == 1:
            d += self.int2char(c << 2)
        return d

    def rsa_encode(self, j_rsakey, string):
        rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
        pubkey = rsa.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
        result = self.b64tohex((base64.b64encode(rsa.encrypt(f'{string}'.encode(), pubkey))).decode())
        return result

    def login(self, user, username, password):
        if not self.cookie_status(user):
            url_token = "https://m.cloud.189.cn/udb/udb_login.jsp"
            params = {
                'pageId': 1,
                'pageKey': 'default',
                'clientType': 'wap',
                'redirectURL': 'https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html'
            }
            r = self.session.get(url_token, params=params)
            pattern = r"https?://[^\s'\"]+"  # 匹配以http或https开头的url
            match = re.search(pattern, r.text)  # 在文本中搜索匹配
            if match:  # 如果找到匹配
                r = self.session.get(match.group())  # 获取匹配的字符串
                pattern = r"<a id=\"j-tab-login-link\"[^>]*href=\"([^\"]+)\""  # 匹配id为j-tab-login-link的a标签，并捕获href引号内的内容
                match = re.search(pattern, r.text)  # 在文本中搜索匹配
                if match:  # 如果找到匹配
                    r = self.session.get(match.group(1))  # 获取捕获的内容
                    j_rsakey = re.findall(r'j_rsaKey" value="(\S+)"', r.text, re.M)[0]
                    self.session.headers.update({"lt": re.findall(r'lt = "(.+?)"', r.text)[0]})

                    url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0',
                        'Referer': 'https://open.e.189.cn/',
                    }
                    data = {
                        "appKey": "cloud",
                        "accountType": '01',
                        "userName": f"{{RSA}}{self.rsa_encode(j_rsakey, username)}",
                        "password": f"{{RSA}}{self.rsa_encode(j_rsakey, password)}",
                        "validateCode": "",
                        "captchaToken": re.findall(r"captchaToken' value='(.+?)'", r.text)[0],
                        "returnUrl": re.findall(r"returnUrl= '(.+?)'", r.text)[0],
                        "mailSuffix": "@189.cn",
                        "paramId": re.findall(r'paramId = "(.+?)"', r.text)[0]
                    }
                    r = self.session.post(url, data=data, headers=headers, timeout=5)
                    if r.json()['result'] == 0:
                        self.initialize.info_message(r.json()['msg'])
                        self.session.get(r.json().get('toUrl'))
                        self.config_option.write_config(user, 'cookies', json.dumps(self.session.cookies.get_dict()))
                    else:
                        raise Exception(f"没有找到url-1:{r.json()['msg']}")
                else:  # 如果没有找到匹配
                    raise Exception("没有找到url-2")
            else:  # 如果没有找到匹配
                raise Exception("没有找到url-3")
        else:
            self.initialize.info_message("cookie还未失效")

    def get_sign_status(self, username):
        """
        获取签到状态
        :params username
        """
        rand = str(round(time.time() * 1000))
        surl = f'https://api.cloud.189.cn/mkt/userSign.action'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
            "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
            "Host": "m.cloud.189.cn",
            "Accept-Encoding": "gzip, deflate",
        }
        params = {
            "rand": rand,
            "clientType": "TELEANDROID",
            "version": "8.6.3",
            "model": "SM-G930K"
        }
        response = self.session.get(surl, headers=headers, params=params)
        net_disk = response.json().get('netdiskBonus')
        is_sign = response.json().get('isSign')
        flag = '已' if is_sign else '未'
        self.initialize.info_message(f'{username}:{flag}签到过,已获得{net_disk}M空间', is_flag=True)
        return is_sign

    def cookie_status(self, user):
        url = 'https://cloud.189.cn/api/portal/listGrow.action'
        headers = {
            'accept': 'application/json;charset=UTF-8',
            'accept-language': 'zh-CN,zh;q=0.9',
            'browser-id': '67d2e3d35f1d64cdd2308ad446bbae13',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        }
        cookie = self.config_option.read_config_key(user, 'cookies')
        if cookie:
            self.session.cookies.update(json.loads(cookie))
            data = self.session.get(url, headers=headers)
            return data and data.status_code == 200 and data.json().get("res_message") == "成功"
        return False

    def sign_in(self, user):
        """
        对云盘进行签到
        :params user:
        :return
        """
        try:
            username = self.config_option.read_config_key(user, 'username')
            password = self.config_option.read_config_key(user, 'password')
            if all([username, password]):
                self.login(user, username, password)
                is_sign = self.get_sign_status(username)
                url = 'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action'
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
                    "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                    "Host": "m.cloud.189.cn",
                    "Accept-Encoding": "gzip, deflate",
                }
                params = {
                    1: {"taskId": "TASK_SIGNIN", "activityId": "ACT_SIGNIN"},
                    2: {"taskId": "TASK_SIGNIN_PHOTOS", "activityId": "ACT_SIGNIN"},
                    3: {"taskId": "TASK_2022_FLDFS_KJ", "activityId": "ACT_SIGNIN"},
                }
                num = 1
                while num < 4 and not is_sign:
                    response = self.session.get(url, headers=headers, params=params[num])
                    description = response.text if "errorCode" in response.text else f"获得{response.json()['description']}M空间"
                    self.initialize.info_message(f"第{num}次抽奖，{description}", is_flag=True)
                    num += 1
            else:
                self.initialize.error_message("天翼云盘:账号或密码不能为空")
        except Exception as er:
            self.initialize.error_message(f"天翼云盘:出现了错误:{er}")

    def init_config(self):
        if not Path.exists(Path.joinpath(self.config_option.file_path, 'config.ini')):
            self.config_option.write_config("账户1", "username", "17630583910")
            self.config_option.write_config("账户1", "password", ".Ai94264744946")
            self.config_option.write_config("账户1", "switch", "0")
            self.config_option.write_config("账户1", "cookies", "")

    def main(self):
        # 判断是否存在文件
        self.initialize.info_message("天翼网盘签到开始")
        sections = self.config_option.read_config_key()
        for index, section in enumerate(sections):
            if self.config_option.read_config_key(section, 'switch', field_type=bool):
                self.sign_in(section)
            else:
                self.initialize.error_message(f'😢第{index + 1}个 switch值为False，不进行任务，跳过该账号')
            self.initialize.info_message("天翼网盘签到结束")
        self.initialize.send_notify("天翼网盘")  # 发送通知


if __name__ == '__main__':
    TianYiYunPan().main()
