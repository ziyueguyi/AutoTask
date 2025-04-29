#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: 天翼网盘.py
Author: WFRobert
Date: 2023/5/19 11:57
cron: 0 10 6 * * ?
new Env('天翼网盘签到脚本');
Description: 天翼网盘脚本,实现每日自动完成天翼网盘签到
Update: 2023/9/1 更新cron
"""
import base64
import importlib.util
import json
import logging
import re
import time
from pathlib import Path

import requests
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
        self.notify = self.import_set.import_notify()
        self.initialize = self.import_set.import_initialize()
        self.file_option = self.import_set.import_file_option()

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

    def login(self,user):
        global href
        url = ""
        urlToken = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
        s = requests.Session()
        r = s.get(urlToken)
        pattern = r"https?://[^\s'\"]+"  # 匹配以http或https开头的url
        match = re.search(pattern, r.text)  # 在文本中搜索匹配
        if match:  # 如果找到匹配
            url = match.group()  # 获取匹配的字符串
        else:  # 如果没有找到匹配
            logging.info("没有找到url")

        r = s.get(url)
        pattern = r"<a id=\"j-tab-login-link\"[^>]*href=\"([^\"]+)\""  # 匹配id为j-tab-login-link的a标签，并捕获href引号内的内容
        match = re.search(pattern, r.text)  # 在文本中搜索匹配
        if match:  # 如果找到匹配
            href = match.group(1)  # 获取捕获的内容
        else:  # 如果没有找到匹配
            logging.info("没有找到href链接")

        r = s.get(href)
        captchaToken = re.findall(r"captchaToken' value='(.+?)'", r.text)[0]
        lt = re.findall(r'lt = "(.+?)"', r.text)[0]
        returnUrl = re.findall(r"returnUrl= '(.+?)'", r.text)[0]
        paramId = re.findall(r'paramId = "(.+?)"', r.text)[0]
        j_rsakey = re.findall(r'j_rsaKey" value="(\S+)"', r.text, re.M)[0]
        s.headers.update({"lt": lt})

        username = self.rsa_encode(j_rsakey, user["username"])
        password = self.rsa_encode(j_rsakey, user["password"])
        url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/76.0',
            'Referer': 'https://open.e.189.cn/',
        }
        data = {
            "appKey": "cloud",
            "accountType": '01',
            "userName": f"{{RSA}}{username}",
            "password": f"{{RSA}}{password}",
            "validateCode": "",
            "captchaToken": captchaToken,
            "returnUrl": returnUrl,
            "mailSuffix": "@163.com",
            "paramId": paramId
        }
        r = s.post(url, data=data, headers=headers, timeout=5)
        if (r.json()['result'] == 0):
            logging.info(r.json()['msg'])
        else:
            logging.info(r.json()['msg'])
        redirect_url = r.json()['toUrl']
        r = s.get(redirect_url)
        return s

    def yunpan_sign(self,user):
        # global description
        try:
            if user["username"] != "" and user["password"] != "":
                s = self.login(user)
                rand = str(round(time.time() * 1000))
                surl = f'https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K'
                url = f'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN&activityId=ACT_SIGNIN'
                url2 = f'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_SIGNIN_PHOTOS&activityId=ACT_SIGNIN'
                url3 = f'https://m.cloud.189.cn/v2/drawPrizeMarketDetails.action?taskId=TASK_2022_FLDFS_KJ&activityId=ACT_SIGNIN'
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
                    "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                    "Host": "m.cloud.189.cn",
                    "Accept-Encoding": "gzip, deflate",
                }
                response = s.get(surl, headers=headers)
                netdiskBonus = response.json()['netdiskBonus']
                if (response.json()['isSign'] == "false"):
                    self.initialize.info_message(f'{user["username"]} 已经签到过了,签到获得{netdiskBonus}M空间')
                else:
                    self.initialize.info_message(f"{user["username"]} 签到成功，签到获得{netdiskBonus}M空间")

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
                    "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                    "Host": "m.cloud.189.cn",
                    "Accept-Encoding": "gzip, deflate",
                }
                response = s.get(url, headers=headers)
                if ("errorCode" in response.text):
                    logging.info(response.text)
                else:
                    description = response.json()['description']
                self.initialize.info_message(f"第一次抽奖获得{description}M空间")

                response = s.get(url2, headers=headers)
                if ("errorCode" in response.text):
                    logging.info(response.text)
                else:
                    description = response.json()['description']
                self.initialize.info_message(f"第二次抽奖获得{description}M空间")

                response = s.get(url3, headers=headers)
                if ("errorCode" in response.text):
                    logging.info(response.text)
                else:
                    description = response.json()['description']
                    self.initialize.info_message(f"第三次抽奖获得{description}M空间")
            else:
                self.initialize.error_message("天翼云盘:账号或密码不能为空")
                return "账号或密码不能为空"
        except Exception as er:
            self.initialize.error_message(f"天翼云盘:出现了错误:{er}")
            return f"出现了错误:{er}"

    def process_user(self, user, num):
        if not user['switch']:
            self.initialize.error_message(f'😢第{num}个 switch值为False，不进行任务，跳过该账号')
            return
        else:
            self.yunpan_sign(user)

    def main(self):
        self.initialize.init()  # 初始化日志系统
        self.file_option.write_file([{'username': None, "password": None,"switch":0}])
        # 判断是否存在文件
        config = self.file_option.read_file()
        num = 0
        for user in config:
            num += 1
            self.process_user(user, num)
            self.initialize.message("\n")
        self.initialize.send_notify("天翼网盘")  # 发送通知


if __name__ == '__main__':
    TianYiYunPan().main()
