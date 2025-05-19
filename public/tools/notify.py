#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
import base64
import hashlib
import hmac
import json
import os
import re
import smtplib
import sys
import threading
import time
import urllib.parse
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from importlib import util
from pathlib import Path

import requests


class Notify:
    def __init__(self):
        tools_path = Path(__file__).resolve().parent
        # 获取当前脚本的上级目录
        public_path = tools_path.parent
        config_option_spc = util.spec_from_file_location('ConfigOption', str(public_path / 'ConfigOption.py'))
        config_option = util.module_from_spec(config_option_spc)
        config_option_spc.loader.exec_module(config_option)
        self.config_option = config_option.ConfigOption(public_path)
        self.mutex = threading.Lock()
        # 通知服务
        # fmt: off
        self.push_config = {
            'HITOKOTO': False,  # 启用一言（随机句子）

            'BARK_PUSH': '',  # bark IP 或设备码，例：https://api.day.app/DxHcxxxxxRxxxxxxcm/
            'BARK_ARCHIVE': '',  # bark 推送是否存档
            'BARK_GROUP': '',  # bark 推送分组
            'BARK_SOUND': '',  # bark 推送声音
            'BARK_ICON': '',  # bark 推送图标

            'CONSOLE': True,  # 控制台输出

            'DD_BOT_SECRET': '',  # 钉钉机器人的 DD_BOT_SECRET
            'DD_BOT_TOKEN': '',  # 钉钉机器人的 DD_BOT_TOKEN

            'FSKEY': '',  # 飞书机器人的 FSKEY

            'GOBOT_URL': '',  # go-cqhttp
            # 推送到个人QQ：http://127.0.0.1/send_private_msg
            # 群：http://127.0.0.1/send_group_msg
            'GOBOT_QQ': '',  # go-cqhttp 的推送群或用户
            # GOBOT_URL 设置 /send_private_msg 时填入 user_id=个人QQ
            #               /send_group_msg   时填入 group_id=QQ群
            'GOBOT_TOKEN': '',  # go-cqhttp 的 access_token

            'GOTIFY_URL': '',  # gotify地址,如https://push.example.de:8080
            'GOTIFY_TOKEN': '',  # gotify的消息应用token
            'GOTIFY_PRIORITY': 0,  # 推送消息优先级,默认为0

            'IGOT_PUSH_KEY': '',  # iGot 聚合推送的 IGOT_PUSH_KEY

            'PUSH_KEY': '',  # server 酱的 PUSH_KEY，兼容旧版与 Turbo 版

            'DEER_KEY': '',  # PushDeer 的 PUSHDEER_KEY
            'DEER_URL': '',  # PushDeer 的 PUSHDEER_URL

            'CHAT_URL': '',  # synology chat url
            'CHAT_TOKEN': '',  # synology chat token

            'PUSH_PLUS_TOKEN': '',  # push+ 微信推送的用户令牌
            'PUSH_PLUS_USER': '',  # push+ 微信推送的群组编码

            'QMSG_KEY': '',  # qmsg 酱的 QMSG_KEY
            'QMSG_TYPE': '',  # qmsg 酱的 QMSG_TYPE

            'QYWX_AM': '',  # 企业微信应用

            'QYWX_KEY': '',  # 企业微信机器人

            'TG_BOT_TOKEN': '',  # tg 机器人的 TG_BOT_TOKEN，例：1407203283:AAG9rt-6RDaaX0HBLZQq0laNOh898iFYaRQ
            'TG_USER_ID': '',  # tg 机器人的 TG_USER_ID，例：1434078534
            'TG_API_HOST': '',  # tg 代理 api
            'TG_PROXY_AUTH': '',  # tg 代理认证参数
            'TG_PROXY_HOST': '',  # tg 机器人的 TG_PROXY_HOST
            'TG_PROXY_PORT': '',  # tg 机器人的 TG_PROXY_PORT

            'AIBOTK_KEY': '',  # 智能微秘书 个人中心的apikey 文档地址：http://wechat.aibotk.com/docs/about
            'AIBOTK_TYPE': '',  # 智能微秘书 发送目标 room 或 contact
            'AIBOTK_NAME': '',  # 智能微秘书  发送群名 或者好友昵称和type要对应好

            'SMTP_SERVER': '',  # SMTP 发送邮件服务器，形如 smtp.exmail.qq.com:465
            'SMTP_SSL': 'false',  # SMTP 发送邮件服务器是否使用 SSL，填写 true 或 false
            'SMTP_EMAIL': '',  # SMTP 收发件邮箱，通知将会由自己发给自己
            'SMTP_PASSWORD': '',  # SMTP 登录密码，也可能为特殊口令，视具体邮件服务商说明而定
            'SMTP_NAME': '',  # SMTP 收发件人姓名，可随意填写
        }
        self.notify_function = []
        # fmt: on

    def get_env_info(self):
        # 首先读取 面板变量 或者 github action 运行变量
        for k in self.push_config:
            if os.getenv(k):
                v = os.getenv(k)
                self.push_config[k] = v

        if self.push_config.get("BARK_PUSH"):
            self.notify_function.append(self.bark)
        if self.push_config.get("CONSOLE"):
            self.notify_function.append(self.console)
        if self.push_config.get("DD_BOT_TOKEN") and self.push_config.get("DD_BOT_SECRET"):
            self.notify_function.append(self.dingding_bot)
        if self.push_config.get("FSKEY"):
            self.notify_function.append(self.feishu_bot)
        if self.push_config.get("GOBOT_URL") and self.push_config.get("GOBOT_QQ"):
            self.notify_function.append(self.go_cqhttp)
        if self.push_config.get("GOTIFY_URL") and self.push_config.get("GOTIFY_TOKEN"):
            self.notify_function.append(self.gotify)
        if self.push_config.get("IGOT_PUSH_KEY"):
            self.notify_function.append(self.iGot)
        if self.push_config.get("PUSH_KEY"):
            self.notify_function.append(self.serverJ)
        if self.push_config.get("DEER_KEY"):
            self.notify_function.append(self.pushdeer)
        if self.push_config.get("CHAT_URL") and self.push_config.get("CHAT_TOKEN"):
            self.notify_function.append(self.chat)
        if self.push_config.get("PUSH_PLUS_TOKEN"):
            self.notify_function.append(self.pushplus_bot)
        if self.push_config.get("QMSG_KEY") and self.push_config.get("QMSG_TYPE"):
            self.notify_function.append(self.qmsg_bot)
        if self.push_config.get("QYWX_AM"):
            self.notify_function.append(self.wecom_app)
        if self.push_config.get("QYWX_KEY"):
            self.notify_function.append(self.wecom_bot)
        if self.push_config.get("TG_BOT_TOKEN") and self.push_config.get("TG_USER_ID"):
            self.notify_function.append(self.telegram_bot)
        if self.push_config.get("AIBOTK_KEY") and self.push_config.get("AIBOTK_TYPE") and self.push_config.get(
                "AIBOTK_NAME"):
            self.notify_function.append(self.aibotk)
        if self.push_config.get("SMTP_SERVER") and self.push_config.get("SMTP_SSL") and self.push_config.get(
                "SMTP_EMAIL") and self.push_config.get(
            "SMTP_PASSWORD") and self.push_config.get("SMTP_NAME"):
            self.notify_function.append(self.smtp)

    # 定义新的 print 函数
    def print_info(self, text, *args, **kw):
        """
        使输出有序进行，不出现多线程同一时间输出导致错乱的问题。
        """
        with self.mutex:
            print(text, *args, **kw)

    def bark(self, title: str, content: str) -> None:
        """
        使用 bark 推送消息。
        """
        if not self.push_config.get("BARK_PUSH"):
            self.print_info("bark 服务的 BARK_PUSH 未设置!!\n取消推送")
            return
        self.print_info("bark 服务启动")

        if self.push_config.get("BARK_PUSH").startswith("http"):
            url = f'{self.push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(title)}/{urllib.parse.quote_plus(content)}'
        else:
            url = f'https://api.day.app/{self.push_config.get("BARK_PUSH")}/{urllib.parse.quote_plus(title)}/{urllib.parse.quote_plus(content)}'

        bark_params = {
            "BARK_ARCHIVE": "isArchive",
            "BARK_GROUP": "group",
            "BARK_SOUND": "sound",
            "BARK_ICON": "icon",
        }
        params = ""
        for pair in filter(
                lambda pairs: pairs[0].startswith("BARK_")
                              and pairs[0] != "BARK_PUSH"
                              and pairs[1]
                              and bark_params.get(pairs[0]),
                self.push_config.items(),
        ):
            params += f"{bark_params.get(pair[0])}={pair[1]}&"
        if params:
            url = url + "?" + params.rstrip("&")
        response = requests.get(url).json()

        if response["code"] == 200:
            self.print_info("bark 推送成功！")
        else:
            self.print_info("bark 推送失败！")

    def console(self, title: str, content: str) -> None:
        """
        使用 控制台 推送消息。
        """
        self.print_info(f"{title}\n\n{content}")

    def dingding_bot(self, title: str, content: str) -> None:
        """
        使用 钉钉机器人 推送消息。
        """
        if not self.push_config.get("DD_BOT_SECRET") or not self.push_config.get("DD_BOT_TOKEN"):
            self.print_info("钉钉机器人 服务的 DD_BOT_SECRET 或者 DD_BOT_TOKEN 未设置!!\n取消推送")
            return
        self.print_info("钉钉机器人 服务启动")

        timestamp = str(round(time.time() * 1000))
        secret_enc = self.push_config.get("DD_BOT_SECRET").encode("utf-8")
        string_to_sign = "{}\n{}".format(timestamp, self.push_config.get("DD_BOT_SECRET"))
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(
            secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f'https://oapi.dingtalk.com/robot/send?access_token={self.push_config.get("DD_BOT_TOKEN")}&timestamp={timestamp}&sign={sign}'
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if not response["errcode"]:
            self.print_info("钉钉机器人 推送成功！")
        else:
            self.print_info("钉钉机器人 推送失败！")

    def feishu_bot(self, title: str, content: str) -> None:
        """
        使用 飞书机器人 推送消息。
        """
        if not self.push_config.get("FSKEY"):
            self.print_info("飞书 服务的 FSKEY 未设置!!\n取消推送")
            return
        self.print_info("飞书 服务启动")

        url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{self.push_config.get("FSKEY")}'
        data = {"msg_type": "text", "content": {"text": f"{title}\n\n{content}"}}
        response = requests.post(url, data=json.dumps(data)).json()

        if response.get("StatusCode") == 0:
            self.print_info("飞书 推送成功！")
        else:
            self.print_info("飞书 推送失败！错误信息如下：\n", response)

    def go_cqhttp(self, title: str, content: str) -> None:
        """
        使用 go_cqhttp 推送消息。
        """
        if not self.push_config.get("GOBOT_URL") or not self.push_config.get("GOBOT_QQ"):
            self.print_info("go-cqhttp 服务的 GOBOT_URL 或 GOBOT_QQ 未设置!!\n取消推送")
            return
        self.print_info("go-cqhttp 服务启动")

        url = f'{self.push_config.get("GOBOT_URL")}?access_token={self.push_config.get("GOBOT_TOKEN")}&{self.push_config.get("GOBOT_QQ")}&message=标题:{title}\n内容:{content}'
        response = requests.get(url).json()

        if response["status"] == "ok":
            self.print_info("go-cqhttp 推送成功！")
        else:
            self.print_info("go-cqhttp 推送失败！")

    def gotify(self, title: str, content: str) -> None:
        """
        使用 gotify 推送消息。
        """
        if not self.push_config.get("GOTIFY_URL") or not self.push_config.get("GOTIFY_TOKEN"):
            self.print_info("gotify 服务的 GOTIFY_URL 或 GOTIFY_TOKEN 未设置!!\n取消推送")
            return
        self.print_info("gotify 服务启动")

        url = f'{self.push_config.get("GOTIFY_URL")}/message?token={self.push_config.get("GOTIFY_TOKEN")}'
        data = {"title": title, "message": content, "priority": self.push_config.get("GOTIFY_PRIORITY")}
        response = requests.post(url, data=data).json()

        if response.get("id"):
            self.print_info("gotify 推送成功！")
        else:
            self.print_info("gotify 推送失败！")

    def iGot(self, title: str, content: str) -> None:
        """
        使用 iGot 推送消息。
        """
        if not self.push_config.get("IGOT_PUSH_KEY"):
            self.print_info("iGot 服务的 IGOT_PUSH_KEY 未设置!!\n取消推送")
            return
        self.print_info("iGot 服务启动")

        url = f'https://push.hellyw.com/{self.push_config.get("IGOT_PUSH_KEY")}'
        data = {"title": title, "content": content}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=data, headers=headers).json()

        if response["ret"] == 0:
            self.print_info("iGot 推送成功！")
        else:
            self.print_info(f'iGot 推送失败！{response["errMsg"]}')

    def serverJ(self, title: str, content: str) -> None:
        """
        通过 serverJ 推送消息。
        """
        if not self.push_config.get("PUSH_KEY"):
            self.print_info("serverJ 服务的 PUSH_KEY 未设置!!\n取消推送")
            return
        self.print_info("serverJ 服务启动")

        data = {"text": title, "desp": content.replace("\n", "\n\n")}
        if self.push_config.get("PUSH_KEY").index("SCT") != -1:
            url = f'https://sctapi.ftqq.com/{self.push_config.get("PUSH_KEY")}.send'
        else:
            url = f'https://sc.ftqq.com/${self.push_config.get("PUSH_KEY")}.send'
        response = requests.post(url, data=data).json()

        if response.get("errno") == 0 or response.get("code") == 0:
            self.print_info("serverJ 推送成功！")
        else:
            self.print_info(f'serverJ 推送失败！错误码：{response["message"]}')

    def pushdeer(self, title: str, content: str) -> None:
        """
        通过PushDeer 推送消息
        """
        if not self.push_config.get("DEER_KEY"):
            self.print_info("PushDeer 服务的 DEER_KEY 未设置!!\n取消推送")
            return
        self.print_info("PushDeer 服务启动")
        data = {"text": title, "desp": content, "type": "markdown", "pushkey": self.push_config.get("DEER_KEY")}
        url = 'https://api2.pushdeer.com/message/push'
        if self.push_config.get("DEER_URL"):
            url = self.push_config.get("DEER_URL")

        response = requests.post(url, data=data).json()

        if len(response.get("content").get("result")) > 0:
            self.print_info("PushDeer 推送成功！")
        else:
            self.print_info("PushDeer 推送失败！错误信息：", response)

    def chat(self, title: str, content: str) -> None:
        """
        通过Chat 推送消息
        """
        if not self.push_config.get("CHAT_URL") or not self.push_config.get("CHAT_TOKEN"):
            self.print_info("chat 服务的 CHAT_URL或CHAT_TOKEN 未设置!!\n取消推送")
            return
        self.print_info("chat 服务启动")
        data = 'payload=' + json.dumps({'text': title + '\n' + content})
        url = self.push_config.get("CHAT_URL") + self.push_config.get("CHAT_TOKEN")
        response = requests.post(url, data=data)

        if response.status_code == 200:
            self.print_info("Chat 推送成功！")
        else:
            self.print_info("Chat 推送失败！错误信息：", response)

    def pushplus_bot(self, title: str, content: str) -> None:
        """
        通过 push+ 推送消息。
        """
        if not self.push_config.get("PUSH_PLUS_TOKEN"):
            self.print_info("PUSHPLUS 服务的 PUSH_PLUS_TOKEN 未设置!!\n取消推送")
            return
        self.print_info("PUSHPLUS 服务启动")

        url = "http://www.pushplus.plus/send"
        data = {
            "token": self.push_config.get("PUSH_PLUS_TOKEN"),
            "title": title,
            "content": content,
            "topic": self.push_config.get("PUSH_PLUS_USER"),
        }
        body = json.dumps(data).encode(encoding="utf-8")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url=url, data=body, headers=headers).json()

        if response["code"] == 200:
            self.print_info("PUSHPLUS 推送成功！")

        else:

            url_old = "http://pushplus.hxtrip.com/send"
            headers["Accept"] = "application/json"
            response = requests.post(url=url_old, data=body, headers=headers).json()

            if response["code"] == 200:
                self.print_info("PUSHPLUS(hxtrip) 推送成功！")

            else:
                self.print_info("PUSHPLUS 推送失败！")

    def qmsg_bot(self, title: str, content: str) -> None:
        """
        使用 qmsg 推送消息。
        """
        if not self.push_config.get("QMSG_KEY") or not self.push_config.get("QMSG_TYPE"):
            self.print_info("qmsg 的 QMSG_KEY 或者 QMSG_TYPE 未设置!!\n取消推送")
            return
        self.print_info("qmsg 服务启动")

        url = f'https://qmsg.zendee.cn/{self.push_config.get("QMSG_TYPE")}/{self.push_config.get("QMSG_KEY")}'
        payload = {"msg": f'{title}\n\n{content.replace("----", "-")}'.encode("utf-8")}
        response = requests.post(url=url, params=payload).json()

        if response["code"] == 0:
            self.print_info("qmsg 推送成功！")
        else:
            self.print_info(f'qmsg 推送失败！{response["reason"]}')

    def wecom_app(self, title: str, content: str) -> None:
        """
        通过 企业微信 APP 推送消息。
        """
        if not self.push_config.get("QYWX_AM"):
            self.print_info("QYWX_AM 未设置!!\n取消推送")
            return
        QYWX_AM_AY = re.split(",", self.push_config.get("QYWX_AM"))
        if 4 < len(QYWX_AM_AY) > 5:
            self.print_info("QYWX_AM 设置错误!!\n取消推送")
            return
        self.print_info("企业微信 APP 服务启动")

        corpid = QYWX_AM_AY[0]
        corpsecret = QYWX_AM_AY[1]
        touser = QYWX_AM_AY[2]
        agentid = QYWX_AM_AY[3]
        try:
            media_id = QYWX_AM_AY[4]
        except IndexError:
            media_id = ""
        wx = WeCom(corpid, corpsecret, agentid)
        # 如果没有配置 media_id 默认就以 text 方式发送
        if not media_id:
            message = title + "\n\n" + content
            response = wx.send_text(message, touser)
        else:
            response = wx.send_mpnews(title, content, media_id, touser)

        if response == "ok":
            self.print_info("企业微信推送成功！")
        else:
            self.print_info("企业微信推送失败！错误信息如下：\n", response)

    def wecom_bot(self, title: str, content: str) -> None:
        """
        通过 企业微信机器人 推送消息。
        """
        if not self.push_config.get("QYWX_KEY"):
            self.print_info("企业微信机器人 服务的 QYWX_KEY 未设置!!\n取消推送")
            return
        self.print_info("企业微信机器人服务启动")

        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.push_config.get('QYWX_KEY')}"
        headers = {"Content-Type": "application/json;charset=utf-8"}
        data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
        response = requests.post(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if response["errcode"] == 0:
            self.print_info("企业微信机器人推送成功！")
        else:
            self.print_info("企业微信机器人推送失败！")

    def telegram_bot(self, title: str, content: str) -> None:
        """
        使用 telegram 机器人 推送消息。
        """
        if not self.push_config.get("TG_BOT_TOKEN") or not self.push_config.get("TG_USER_ID"):
            self.print_info("tg 服务的 bot_token 或者 user_id 未设置!!\n取消推送")
            return
        self.print_info("tg 服务启动")

        if self.push_config.get("TG_API_HOST"):
            url = f"https://{self.push_config.get('TG_API_HOST')}/bot{self.push_config.get('TG_BOT_TOKEN')}/sendMessage"
        else:
            url = (
                f"https://api.telegram.org/bot{self.push_config.get('TG_BOT_TOKEN')}/sendMessage"
            )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {
            "chat_id": str(self.push_config.get("TG_USER_ID")),
            "text": f"{title}\n\n{content}",
            "disable_web_page_preview": "true",
        }
        proxies = None
        if self.push_config.get("TG_PROXY_HOST") and self.push_config.get("TG_PROXY_PORT"):
            if self.push_config.get("TG_PROXY_AUTH") is not None and "@" not in self.push_config.get(
                    "TG_PROXY_HOST"
            ):
                self.push_config["TG_PROXY_HOST"] = (
                        self.push_config.get("TG_PROXY_AUTH")
                        + "@"
                        + self.push_config.get("TG_PROXY_HOST")
                )
            proxyStr = "http://{}:{}".format(
                self.push_config.get("TG_PROXY_HOST"), self.push_config.get("TG_PROXY_PORT")
            )
            proxies = {"http": proxyStr, "https": proxyStr}
        response = requests.post(
            url=url, headers=headers, params=payload, proxies=proxies
        ).json()

        if response["ok"]:
            self.print_info("tg 推送成功！")
        else:
            self.print_info("tg 推送失败！")

    def aibotk(self, title: str, content: str) -> None:
        """
        使用 智能微秘书 推送消息。
        """
        if not self.push_config.get("AIBOTK_KEY") or not self.push_config.get(
                "AIBOTK_TYPE") or not self.push_config.get(
            "AIBOTK_NAME"):
            self.print_info("智能微秘书 的 AIBOTK_KEY 或者 AIBOTK_TYPE 或者 AIBOTK_NAME 未设置!!\n取消推送")
            return
        self.print_info("智能微秘书 服务启动")

        if self.push_config.get("AIBOTK_TYPE") == 'room':
            url = "https://api-bot.aibotk.com/openapi/v1/chat/room"
            data = {
                "apiKey": self.push_config.get("AIBOTK_KEY"),
                "roomName": self.push_config.get("AIBOTK_NAME"),
                "message": {"type": 1, "content": f'【青龙快讯】\n\n${title}\n${content}'}
            }
        else:
            url = "https://api-bot.aibotk.com/openapi/v1/chat/contact"
            data = {
                "apiKey": self.push_config.get("AIBOTK_KEY"),
                "name": self.push_config.get("AIBOTK_NAME"),
                "message": {"type": 1, "content": f'【青龙快讯】\n\n${title}\n${content}'}
            }
        body = json.dumps(data).encode(encoding="utf-8")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url=url, data=body, headers=headers).json()
        self.print_info(response)
        if response["code"] == 0:
            self.print_info("智能微秘书 推送成功！")
        else:
            self.print_info(f'智能微秘书 推送失败！{response["error"]}')

    def smtp(self, title: str, content: str) -> None:
        """
        使用 SMTP 邮件 推送消息。
        """
        if not self.push_config.get("SMTP_SERVER") or not self.push_config.get("SMTP_SSL") or not self.push_config.get(
                "SMTP_EMAIL") or not self.push_config.get("SMTP_PASSWORD") or not self.push_config.get("SMTP_NAME"):
            self.print_info(
                "SMTP 邮件 的 SMTP_SERVER 或者 SMTP_SSL 或者 SMTP_EMAIL 或者 SMTP_PASSWORD 或者 SMTP_NAME 未设置!!\n取消推送")
            return
        self.print_info("SMTP 邮件 服务启动")

        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = formataddr(
            (Header(self.push_config.get("SMTP_NAME"), 'utf-8').encode(), self.push_config.get("SMTP_EMAIL")))
        message['To'] = formataddr(
            (Header(self.push_config.get("SMTP_NAME"), 'utf-8').encode(), self.push_config.get("SMTP_EMAIL")))
        message['Subject'] = Header(title, 'utf-8')

        try:
            smtp_server = smtplib.SMTP_SSL(self.push_config.get("SMTP_SERVER")) if self.push_config.get(
                "SMTP_SSL") == 'true' else smtplib.SMTP(self.push_config.get("SMTP_SERVER"))
            smtp_server.login(self.push_config.get("SMTP_EMAIL"), self.push_config.get("SMTP_PASSWORD"))
            smtp_server.sendmail(self.push_config.get("SMTP_EMAIL"), self.push_config.get("SMTP_EMAIL"),
                                 message.as_bytes())
            smtp_server.close()
            self.print_info("SMTP 邮件 推送成功！")
        except Exception as e:
            self.print_info(f'SMTP 邮件 推送失败！{e}')

    def one(self) -> str:
        """
        获取一条一言。
        :return:
        """
        url = "https://v1.hitokoto.cn/"
        res = requests.get(url).json()
        return res["hitokoto"] + "    ----" + res["from"]

    def read_config(self, config=None):
        """
        判断是否通知
        """
        if config is None:
            # 获取主运行脚本的文件路径
            config = self.config_option.read_config_key(section="系统配置", key="notice")
            config = config == sys.argv[0].split('.')[0] or config == "all"

        return config

    def send(self, title: str, content: str, config_notice: bool = None) -> None:
        if not self.read_config(config_notice):
            self.print_info(f"{title} 已设置不进行推送，如需打开请配置notice=True")
            return
        elif not content:
            self.print_info(f"{title} 推送内容为空！")
            return
        else:
            # 根据标题跳过一些消息推送，环境变量：SKIP_PUSH_TITLE 用回车分隔
            if os.getenv("SKIP_PUSH_TITLE"):
                if title in re.split("\n", os.getenv("SKIP_PUSH_TITLE")):
                    self.print_info(f"{title} 在SKIP_PUSH_TITLE环境变量内，跳过推送！")
                    return
            content += "\n\n" + self.one() if self.push_config.get("HITOKOTO") else ""
            ts = [threading.Thread(target=mode, args=(title, content), name=mode.__name__) for mode in
                  self.notify_function]
            [t.start() for t in ts]
            [t.join() for t in ts]

    def run(self):
        self.get_env_info()
        self.send("title", "content")


class WeCom:
    def __init__(self, corpid, corpsecret, agentid):
        self.CORPID = corpid
        self.CORPSECRET = corpsecret
        self.AGENTID = agentid

    def get_access_token(self):
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        values = {
            "corpid": self.CORPID,
            "corpsecret": self.CORPSECRET,
        }
        req = requests.post(url, params=values)
        data = json.loads(req.text)
        return data["access_token"]

    def send_text(self, message, touser="@all"):
        send_url = (
                "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="
                + self.get_access_token()
        )
        send_values = {
            "touser": touser,
            "msgtype": "text",
            "agentid": self.AGENTID,
            "text": {"content": message},
            "safe": "0",
        }
        send_msges = bytes(json.dumps(send_values), "utf-8")
        respone = requests.post(send_url, send_msges)
        respone = respone.json()
        return respone["errmsg"]

    def send_mpnews(self, title, message, media_id, touser="@all"):
        send_url = (
                "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="
                + self.get_access_token()
        )
        send_values = {
            "touser": touser,
            "msgtype": "mpnews",
            "agentid": self.AGENTID,
            "mpnews": {
                "articles": [
                    {
                        "title": title,
                        "thumb_media_id": media_id,
                        "author": "Author",
                        "content_source_url": "",
                        "content": message.replace("\n", "<br/>"),
                        "digest": message,
                    }
                ]
            },
        }
        send_msges = bytes(json.dumps(send_values), "utf-8")
        respone = requests.post(send_url, send_msges)
        respone = respone.json()
        return respone["errmsg"]


if __name__ == "__main__":
    Notify().run()
