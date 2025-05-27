#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: 吾爱破解.py
Author: WFRobert
Date: 2023/3/9 15:01
cron: 0 25 6 * * ?
new Env('吾爱破解');
Description: 52pojie自动签到,实现每日自动签到52pojie
const $ = new Env('吾爱破解')
cron: 19 7 * * *
"""
import json
import random
import subprocess
import sys
import time
from importlib import util
from pathlib import Path

from curl_cffi import requests
from lxml import html
from playwright.sync_api import sync_playwright, Page


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

    @staticmethod
    def convert_requests_cookies_to_playwright(requests_cookies):
        """
        coookies转换，转为playwright可用cookies
        :param requests_cookies:
        :return:
        """
        cookies = []
        for c in requests_cookies:
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain if c.domain.startswith('.') else '.' + c.domain if c.domain else 'www.52pojie.cn',
                "path": c.path,
                "expires": c.expires if c.expires else -1,
                "httpOnly": bool(c._rest.get("http_only", c.name in ['htVC_2132_saltkey', 'htVC_2132_auth'])),
                "secure": bool(c.secure or c.name in ['htVC_2132_saltkey', 'htVC_2132_auth']),
                "sameSite": "Lax" if c.name in ['wzws_sessionid', 'htVC_2132_saltkey', 'htVC_2132_auth'] else 'None'
            })
        return cookies

    @staticmethod
    def bypass_anti_crawler(page: Page):
        """
        浏览器页面模拟，绕过js反扒检测
        :param page:
        :return:
        """
        """注入 JS 绕过反爬虫检测"""
        page.add_init_script("""
            // 删除 webdriver 标志
            delete navigator.__proto__.webdriver;
        window.devicePixelRatio = 1.25;
            // 模拟浏览器的 getBattery API，用于绕过反爬虫检测。
            // 返回一个 Promise，模拟电池信息（始终为固定值）。
            navigator.__proto__.getBattery = () => Promise.resolve({
                charging: true,                  // 电池正在充电
                level: 0.7,                      // 电池电量为 70%
                chargingTime: Infinity,          // 剩余充电时间为无限（表示已充满）
                dischargingTime: null            // 放电时间未确定
            });
            
            // 设置 window.__playwright_init__ 标志，表明页面由 Playwright 控制。
            // 某些网站会检测此标志来判断是否是自动化行为，设置后可帮助绕过部分检测机制。
            window.__playwright_init__ = true;

            // 设置 window.chrome
            window.chrome = {
                runtime: {}
            };

            // 模拟 hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                value: 8,
                configurable: false,
                writable: false
            });

            Object.defineProperty(navigator, 'plugins', {
                value: [1, 2, 3, 4, 5],
            });
            window.devicePixelRatio = 1.25;
            // 模拟 language
            Object.defineProperty(navigator, 'languages', {
                value: ["zh-CN", "zh", "en-US", "en"],
                configurable: false,
                writable: false
            });

            // 模拟权限查询
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters);

            // 模拟媒体设备
            navigator.mediaDevices.getUserMedia = () => Promise.resolve({});
        """)
        return page

    def get_cookies(self):
        """
        获取加签的cookies
        :return:
        """
        playwright_cookies = self.convert_requests_cookies_to_playwright(self.session.cookies.jar)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--disable-automation"
                "--disable-background-networking",
                "--disable-expose-autofill-popup"
            ])  # headless=True 表示无头模式
            context = browser.new_context( accept_downloads=True, java_script_enabled=True)
            # 设置 cookies
            context.add_cookies(playwright_cookies)
            # # 注入脚本，模拟浏览器指纹(可用)
            page = self.bypass_anti_crawler(context.new_page())
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
            })
            page.goto('https://www.52pojie.cn/home.php?mod=task&item=new')
            # 等待导航完成
            page.wait_for_timeout(2000)
            # time.sleep(10)
            page.reload()
            flag = False
            try:
                page.wait_for_selector("//a[contains(text(), '新任务')]")
                cookies = context.cookies()
                if list(filter(lambda s: s["name"] == 'wzws_sid', cookies)):
                    self.session.cookies.update({val["name"]: val["value"] for val in cookies})
                    flag = True
                else:
                    exit()
            except TimeoutError:
                self.initialize.error_message(f"账号Cookie 失效", is_flag=True)
            finally:
                # 截图保存
                page.screenshot(path=r"baidu_search_result.png")
                browser.close()
                return flag

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

    def run(self):
        self.initialize.info_message("吾爱破解签到开始")
        account_list = self.config_option.read_config_key()
        self.check_and_install_chromium()
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                if self.get_cookies() and self.get_task_list():
                    self.sign()
                self.get_account_info()
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("吾爱破解签到结束")
        self.initialize.send_notify("吾爱破解")

    def check_and_install_chromium(self):
        """
        软件自检

        """
        try:
            with sync_playwright() as p:
                # 尝试启动一次 Chromium（headless 模式）
                browser = p.chromium.launch(headless=True)
                self.initialize.info_message("✅ Chromium 已安装...")
                browser.close()
        except Exception as e:
            if "Chromium is not installed" in str(e):
                self.initialize.info_message("⚠️ Chromium 未安装，正在安装...")
                subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                self.initialize.info_message("✅ Chromium 安装完成")
            else:
                self.initialize.info_message("❌ 出现其他错误:", str(e))
                exit()

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


if __name__ == '__main__':
    Template().run()
