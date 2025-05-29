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
import os.path
import platform
import random
import time
from importlib import util
from pathlib import Path
from zipfile import ZipFile

import undetected_chromedriver as uc
from curl_cffi import requests
from lxml import html
from selenium.webdriver.support.ui import WebDriverWait


# 👇 禁止析构函数中的 quit()
def noop(self):
    pass


uc.Chrome.__del__ = noop  # 👈 关键一行


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
    def convert_session_cookies_to_selenium(requests_cookies):
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

    def take_screenshot(self, driver, step_name):
        filename = f"{step_name}.png"
        driver.save_screenshot(filename)
        self.initialize.info_message(f"📸 已截图保存为：{filename}")

    def get_cookie(self):
        """
        获取加签的cookies
        :return:
        """
        flag = False

        cookies = self.convert_session_cookies_to_selenium(self.session.cookies.jar)
        time.sleep(random.randint(1, 2))
        driver = self.setup_browser(headless=True)  # 服务器部署时请保持 True
        try:
            driver.get("https://www.52pojie.cn/home.php?mod=task&item=new")
            driver = self.load_cookies(driver, cookies)
            self.wait_for_js_complete(driver)
            time.sleep(5)
            driver.refresh()
            self.wait_for_js_complete(driver)
            time.sleep(5)
            self.convert_selenium_cookies_to_session(driver)
            self.take_screenshot(driver, "登录界面")
            flag = True
        except Exception as e:
            self.initialize.error_message(f"❌ 获取 cookies 异常: {str(e)}")
            self.take_screenshot(driver, "错误页面")
        finally:
            # 关闭浏览器驱动
            driver.quit()
            self.initialize.info_message("🚪 浏览器已关闭")
            return flag

    def convert_selenium_cookies_to_session(self, driver):
        # 获取当前 cookies（Selenium 格式）
        selenium_cookies = driver.get_cookies()

        # 转换为 requests 可用格式
        cookie_dict = {}
        for cookie in selenium_cookies:
            cookie_dict[cookie['name']] = cookie['value']

        # 更新到 self.session 的 cookies 中
        self.session.cookies.update(cookie_dict)
        self.initialize.info_message("✅ 已将 Selenium Cookies 更新至 Session")

    @staticmethod
    def load_cookies(driver, cookies):
        """
        加载本地保存的 Cookies（用于保持登录状态）
        """

        for cookie in cookies:
            if 'expiry' in cookie:
                cookie['expirationDate'] = cookie.pop('expiry')
            driver.add_cookie({
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie.get('domain', '.52pojie.cn'),
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', False),
                'httpOnly': cookie.get('httpOnly', False),
                'sameSite': cookie.get('sameSite', 'Lax')
            })
        return driver

    @staticmethod
    def get_os():
        system = platform.system()
        if system == "Linux":
            return "linux"
        elif system == "Windows":
            return "windows"
        elif system == "Darwin":
            return "macos"
        else:
            return "unknown"

    def download_and_extract(self, url, extract_to: Path):
        """
        根据链接下载 ZIP 文件并解压
        :param url: ZIP 文件的下载地址
        :param extract_to: 解压到的目标路径，默认为当前目录下以 ZIP 名命名的文件夹
        """
        # 获取文件名
        file_path = Path.joinpath(extract_to, url.split('/')[-1].split('-')[0])
        if file_path.exists():
            self.initialize.info_message(f"📦 文件已存在，跳过下载：{file_path}")
            return file_path
        else:
            self.initialize.info_message(f"📥 正在从 {url} 下载文件...")
            response = requests.get(url, stream=True)
            if response.status_code != 200:
                raise Exception(f"❌ 下载失败，HTTP 状态码: {response.status_code}")
            else:
                # # 保存 ZIP 文件
                zip_path = extract_to / url.split('/')[-1]
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                self.initialize.info_message(f"📦 文件已保存至：{zip_path}")
                return self.extract_file(zip_path, file_path)

    def extract_file(self, zip_path, file_path):
        """

        :param zip_path:
        :param file_path:
        :return:
        """
        # 设置解压路径
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        file_path = zip_path
        # 解压 ZIP 文件
        self.initialize.info_message(f"📂 开始解压到：{zip_path.parent}")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(zip_path.parent)
        Path.rename(zip_path.with_suffix(''), file_path)
        self.initialize.info_message("✅ 解压完成")

        # 可选：删除 ZIP 文件
        zip_path.unlink()
        self.initialize.info_message(f"🗑️ 已删除压缩包：{zip_path}")
        return file_path

    def get_environment_variables(self):
        """
        部署基础所需环境
        :return:
        """
        # 🔧 指定本地 chromedriver 路径（Windows 示例）
        platform_os = self.get_os()
        if platform_os == 'linux':
            chrome = 'https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.55/linux64/chrome-linux64.zip'
            driver = 'https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.55/linux64/chromedriver-linux64.zip'
            base = Path.joinpath(Path('.'), 'files', 'linux')
            driver_name = 'chromedriver'
            browser_name = 'chrome'
        elif platform_os == 'windows':
            chrome = 'https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.55/win64/chrome-win64.zip'
            driver = 'https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.55/win64/chromedriver-win64.zip'
            base = Path.joinpath(Path('.'), 'files', 'windows')
            driver_name = 'chromedriver.exe'
            browser_name = 'chrome.exe'
        else:
            exit()
        browser_path = Path.joinpath(self.download_and_extract(chrome, extract_to=base), browser_name)
        driver_path = Path.joinpath(self.download_and_extract(driver, extract_to=base), driver_name)
        return f"{driver_path}", f"{browser_path}"

    def setup_browser(self, headless=False):
        """
        初始化浏览器实例（自动适配本地 Chrome 版本）
        :param headless: 是否启用无头模式
        """
        options = uc.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=zh-CN')
        if headless:
            options.add_argument('--headless=new')  # 新一代无头模式
        driver_path, browser_path = self.get_environment_variables()
        # 设置 User-Agent（模拟真实用户）
        options.add_argument(f'--user-agent={self.session.headers.get("User-Agent")}')
        driver = uc.Chrome(options=options, driver_executable_path=driver_path, browser_executable_path=browser_path)
        self.initialize.info_message("✅ 浏览器初始化完成")

        return driver

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
        for ind, sec in enumerate(account_list):
            self.initialize.info_message(f"共{len(account_list)}个账户，第{ind + 1}个账户：{sec},")
            self.session.cookies.update(json.loads(self.config_option.read_config_key(section=sec, key="cookies")))
            try:
                if self.get_cookie() and self.get_task_list():
                    self.sign()
                self.get_account_info()
            except Exception as e:
                self.initialize.error_message(e.__str__(), is_flag=True)
        self.initialize.info_message("吾爱破解签到结束")
        self.initialize.send_notify("吾爱破解")

    def wait_for_js_complete(self, driver, timeout=120):
        """
        等待 JavaScript 加载完成
        """
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            self.initialize.info_message("✅ JavaScript 加载完成")
        except Exception as e:
            self.initialize.error_message(f"❌ JavaScript 加载超时: {str(e)}")
            self.take_screenshot(driver, "JS加载失败")
            raise

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
