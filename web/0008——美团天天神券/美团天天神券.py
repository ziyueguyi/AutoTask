# -*- coding: utf-8 -*-
"""
# @项目名称 :AutoTask
# @文件名称 :美团天天神券.py
# @文件介绍 :美团外卖天天神券：签到领豆、每日签到、兑必中符、抢红包
# Token 获取（推荐 H5，主站常登不上）：
#   1. 手机模式打开 https://h5.waimai.meituan.com/ 并登录
#   2. F12 → Network → 刷新，点开任意 i.waimai.meituan.com 请求
#   3. 从 Cookie 复制 token= 后面的值（不要整段 Cookie 也行，脚本也能从 Cookie 串里解析 token）
# 青龙环境变量（前缀 MT）：
#   MT_account            必填。纯 token / 含 token= 的 Cookie 串 / {"token":"xxx","wm_latitude":"30657401","wm_longitude":"104065827"}
#   MT_latitude           默认纬度（去小数点），如成都 30657401；账号 JSON 可覆盖
#   MT_longitude          默认经度（去小数点），如成都 104065827
#   MT_propId             兑换必中符类型，默认 5（15 元）；常见 2/3/4/5
#   MT_exchangeCoinNumber 兑换所需豆数，默认 1800
#   MT_setexchangedou     豆攒够多少才兑换，默认 1800
#   MT_grab_big           填 1 开启大额监测（有 10/15 元必中符时），默认关闭
#   MT_notify             通知开关，填 1 开启
const $ = new Env('美团天天神券')
cron: 5 11,17,21 * * *
"""
import os
import random
import time
from datetime import datetime
from importlib import util
from pathlib import Path
from urllib.parse import urlencode

from curl_cffi import requests


class MeituanShenquan:
    def __init__(self) -> None:
        self.BASE = "https://i.waimai.meituan.com"
        self.PAR_ACTIVITY_ID = "Gh1tkq-wvFU2xEP_ZPzHPQ"
        self.WM_CTYPE = "mtandroid"
        self.PORTRAIT_ID = "498"
        public_path = Path(__file__).resolve().parent.parent.parent / "public"
        import_set_spc = util.spec_from_file_location("ImportSet", str(public_path / "ImportSet.py"))
        import_set_module = util.module_from_spec(import_set_spc)
        import_set_spc.loader.exec_module(import_set_module)
        self.import_set = import_set_module.ImportSet("MT")
        self.initialize = self.import_set.import_initialize()
        self.env_name = self.initialize.env_key("account")
        self.default_lat = os.getenv(self.initialize.env_key("latitude"), "30657401").strip()
        self.default_lng = os.getenv(self.initialize.env_key("longitude"), "104065827").strip()
        self.default_prop_id = int(os.getenv(self.initialize.env_key("propId"), "5") or "5")
        self.exchange_coin = int(os.getenv(self.initialize.env_key("exchangeCoinNumber"), "1800") or "1800")
        self.set_exchange_dou = int(os.getenv(self.initialize.env_key("setexchangedou"), "1800") or "1800")
        self.grab_big = os.getenv(self.initialize.env_key("grab_big"), "").strip() == "1"
        self.session = requests.Session(timeout=15)
        self.session.headers.update({
            "Host": "i.waimai.meituan.com",
            "User-Agent": "MeituanGroup/11.9.208",
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded",
        })

    def emit(self, text: str, ok: bool = True) -> None:
        if ok:
            self.initialize.info_message(text, is_flag=True)
        else:
            self.initialize.error_message(text, is_flag=True)

    def post(self, path: str, data: dict) -> dict:
        response = self.session.post(f"{self.BASE}{path}", data=urlencode(data))
        try:
            return response.json()
        except Exception:
            return {"code": -1, "msg": f"HTTP {response.status_code} {response.text[:200]}"}

    @staticmethod
    def resolve_account(account: dict) -> tuple[str, str, str]:
        token = (
            account.get("token")
            or account.get("mt_c_token")
            or account.get("w_token")
            or account.get("oops")
            or ""
        )
        lat = str(account.get("wm_latitude") or account.get("latitude") or "")
        lng = str(account.get("wm_longitude") or account.get("longitude") or "")
        return str(token).strip(), lat.strip(), lng.strip()

    def sign_for_beans(self, token: str) -> None:
        data = self.post("/cfeplay/playcenter/batchgrabred/drawPoints/v2", {"token": token})
        code = data.get("code")
        msg = data.get("msg") or ""
        if code == 0:
            self.emit(f"签到领豆：{msg or '成功'}")
        elif code == 1:
            self.emit(f"签到领豆：未到时间或今日已领完（每天最多 7 次，间隔约半小时）")
        elif code == 7:
            self.emit(f"签到领豆失败：token 失效，请从 h5.waimai.meituan.com 重新获取", ok=False)
        else:
            self.emit(f"签到领豆失败：{msg or data}", ok=False)

    def get_batch_id(self, token: str, lat: str, lng: str) -> str | None:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/corepage",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_ctype": self.WM_CTYPE,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
            },
        )
        code = data.get("code")
        if code == 0:
            batch_id = (data.get("data") or {}).get("batchId")
            if batch_id:
                self.emit(f"活动场次 batchId：{batch_id}")
                awards = (data.get("data") or {}).get("awardInfos") or []
                for item in awards:
                    yuan = item.get("showPriceNumberYuan")
                    left = item.get("leftStock")
                    total = item.get("totalStock")
                    if yuan is not None:
                        self.emit(f"红包池 {yuan} 元：总量 {total}，剩余 {left}")
                return str(batch_id)
            self.emit("当前非限时抢红包时段，已完成签到相关流程")
            return None
        if code == 7 or (code == 1 and data.get("subcode") == -1):
            self.emit(f"获取活动失败：token 无效或未登录（{data.get('msg')}）", ok=False)
            return None
        self.emit(f"获取活动失败：{data.get('msg') or data}", ok=False)
        return None

    def daily_sign_prop(self, token: str, lat: str, lng: str) -> None:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/doAction",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
                "action": "SiginInGetProp",
            },
        )
        if data.get("code") == 0:
            days = (data.get("data") or {}).get("signDays")
            if days:
                self.emit(f"每日签到：成功，本周已签 {days} 天")
            else:
                self.emit("每日签到：今日已签到")
        else:
            self.emit(f"每日签到：{data.get('msg') or data}", ok=data.get("code") == 0)

    def query_beans(self, token: str, lat: str, lng: str) -> int:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/myRedBeanRecords",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
                "userPortraitId": self.PORTRAIT_ID,
                "pageNum": "1",
            },
        )
        if data.get("code") == 0 and data.get("subcode") == 0:
            info = data.get("data") or {}
            total = int(info.get("totalObtainAmount") or 0)
            used = int(info.get("usedAmount") or 0)
            expired = int(info.get("expiredAmount") or 0)
            left = total - used - expired
            self.emit(f"红包豆：总获得 {total}，已用 {used}，过期 {expired}，剩余 {left}")
            return left
        self.emit(f"查询红包豆失败：{data.get('msg') or data}", ok=False)
        return 0

    def exchange_prop(self, token: str, lat: str, lng: str, prop_id: int) -> None:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/exchange",
            {
                "wm_actual_longitude": lng,
                "wm_actual_latitude": lat,
                "exchangeRuleId": "",
                "propId": str(prop_id),
                "exchangeCoinNumber": str(self.exchange_coin),
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_ctype": self.WM_CTYPE,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
            },
        )
        code, sub = data.get("code"), data.get("subcode")
        msg = data.get("msg") or ""
        if code == 0 and sub == 0:
            self.emit(f"兑换必中符成功：{msg}")
        elif code == 1 and sub == 13:
            self.emit(f"兑换必中符：非兑换时段（{msg}）")
        elif code == 1 and sub == -1:
            self.emit(f"兑换必中符失败：豆不足或库存空（{msg}）", ok=False)
            if prop_id > 2:
                lower = prop_id - 1
                self.emit(f"尝试降级兑换 propId={lower}")
                self.exchange_prop(token, lat, lng, lower)
        else:
            self.emit(f"兑换必中符失败：{msg or data}", ok=False)

    def query_props(self, token: str, lat: str, lng: str) -> int:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/myProps",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
            },
        )
        prop_for_use = 1
        items = data.get("data") if data.get("code") == 0 else None
        if isinstance(items, list) and items:
            valid = 0
            for index, item in enumerate(items):
                if item.get("status") == 1:
                    valid += 1
                    if valid == 1:
                        prop_for_use = int(item.get("propId") or 1)
                    self.emit(
                        f"必中符#{index + 1}：{item.get('propName')}，"
                        f"propId={item.get('propId')}，过期 {item.get('expireTime')}"
                    )
            self.emit(f"道具库有效必中符 {valid} 个，本次将使用 propId={prop_for_use}")
        else:
            self.emit("道具库无有效必中符，将拼手气抢红包")
        return prop_for_use

    def draw_lottery(self, token: str, lat: str, lng: str, batch_id: str, prop_id: int) -> int:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/drawlottery",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
                "batchId": batch_id,
                "isShareLink": "true",
                "propType": "1",
                "propId": str(prop_id),
            },
        )
        code, sub = data.get("code"), data.get("subcode")
        msg = data.get("msg") or ""
        if code == 0:
            info = data.get("data") or {}
            price = int(info.get("showPriceNumber") or 0)
            self.emit(
                f"抢红包成功：{info.get('name')} / {info.get('showTitle')}，"
                f"限制 {info.get('priceLimitdesc')}，面值 {price / 100:.2f} 元"
            )
            return price
        if code == 7 or (code == 1 and sub == -1):
            self.emit(f"抢红包失败：{msg or 'token/次数异常'}", ok=False)
        else:
            self.emit(f"抢红包：{msg or data}", ok=False)
        return 0

    def accept_or_to_bean(self, token: str, lat: str, lng: str, batch_id: str, price: int) -> None:
        if price <= 0:
            return
        if price < 500:
            data = self.post(
                "/cfeplay/playcenter/batchgrabred/redToBean",
                {
                    "parActivityId": self.PAR_ACTIVITY_ID,
                    "wm_latitude": lat,
                    "wm_longitude": lng,
                    "token": token,
                    "batchId": batch_id,
                },
            )
            if data.get("code") == 0:
                self.emit("小额红包已转红包豆")
            else:
                self.emit(f"转豆：{data.get('msg') or data}", ok=False)
            return
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/acceptRed",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
                "batchId": batch_id,
            },
        )
        if data.get("code") == 0:
            self.emit("红包已发放到红包库")
        else:
            self.emit(f"入库：{data.get('msg') or data}", ok=False)

    def query_rewards(self, token: str) -> None:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/myreward",
            {"parActivityId": self.PAR_ACTIVITY_ID, "token": token},
        )
        if data.get("code") != 0:
            self.emit(f"查询红包库失败：{data.get('msg') or data}", ok=False)
            return
        items = ((data.get("data") or {}).get("myawardInfos") or [])
        if not items:
            self.emit("红包库为空")
            return
        valid = 0
        for index, item in enumerate(items):
            if not item.get("status"):
                valid += 1
                left_min = round(float(item.get("leftTime") or 0) / 60000, 1)
                self.emit(
                    f"红包#{index + 1}：{item.get('name')} "
                    f"{item.get('showPriceNumberYuan')} 元，剩余 {left_min} 分钟"
                )
        self.emit(f"红包库共 {len(items)} 个，有效 {valid} 个")

    def send_task_bean(self, token: str, lat: str, lng: str) -> None:
        data = self.post(
            "/cfeplay/playcenter/batchgrabred/sendTaskRedBean",
            {
                "parActivityId": self.PAR_ACTIVITY_ID,
                "wm_latitude": lat,
                "wm_longitude": lng,
                "token": token,
                "portraitId": self.PORTRAIT_ID,
            },
        )
        status = data.get("status")
        if status == 0:
            self.emit(f"浏览任务领豆：成功 +{data.get('sendBeanCount') or 0}")
        elif status == 1:
            self.emit(f"浏览任务领豆：今日已领（{data.get('msg') or ''}）")
        else:
            self.emit(f"浏览任务领豆：{data.get('msg') or data}", ok=False)

    def maybe_wait_big(self, token: str, lat: str, lng: str, prop_id: int) -> None:
        """有 10/15 元必中符且开启 MT_grab_big 时，简单监测大额余量。"""
        if not self.grab_big or prop_id not in (3, 5):
            return
        now = datetime.now()
        windows = [
            (now.replace(hour=17, minute=0, second=0, microsecond=0),
             now.replace(hour=20, minute=49, second=0, microsecond=0)),
            (now.replace(hour=21, minute=0, second=0, microsecond=0),
             now.replace(hour=23, minute=59, second=0, microsecond=0)),
        ]
        in_window = any(start <= now <= end for start, end in windows)
        if not in_window:
            self.emit("大额监测：当前不在 17:00-20:49 / 21:00-23:59，跳过")
            return
        self.emit(f"大额监测开启：当前必中符 propId={prop_id}，最多轮询 30 次")
        for _ in range(30):
            data = self.post(
                "/cfeplay/playcenter/batchgrabred/corepage",
                {
                    "parActivityId": self.PAR_ACTIVITY_ID,
                    "wm_ctype": self.WM_CTYPE,
                    "wm_latitude": lat,
                    "wm_longitude": lng,
                    "token": token,
                },
            )
            awards = ((data.get("data") or {}).get("awardInfos") or [])
            left_map = {}
            for item in awards:
                try:
                    yuan = int(float(item.get("showPriceNumberYuan") or 0))
                except (TypeError, ValueError):
                    continue
                left_map[yuan] = item.get("leftStock")
            # 15 元还有、更高面额已空 → 保底 15；否则继续等
            fifteen_left = left_map.get(15)
            thirty_left = left_map.get(30)
            fifty_left = left_map.get(50)
            self.emit(f"监测余量：15={fifteen_left} 30={thirty_left} 50={fifty_left}")
            if fifteen_left == 0 or (thirty_left == 0 and fifty_left == 0 and fifteen_left is not None):
                self.emit("大额监测结束，进入抢保底")
                return
            time.sleep(2 + random.random())

    def run_account(self, account_name: str, account: dict) -> None:
        token, lat, lng = self.resolve_account(account)
        lat = lat or self.default_lat
        lng = lng or self.default_lng
        if not token:
            self.emit(f"{account_name} 缺少 token", ok=False)
            return
        self.emit(f"{account_name} 开始（lat={lat}, lng={lng}）")
        self.sign_for_beans(token)
        batch_id = self.get_batch_id(token, lat, lng)
        self.daily_sign_prop(token, lat, lng)
        left_dou = self.query_beans(token, lat, lng)
        if left_dou >= self.set_exchange_dou:
            self.exchange_prop(token, lat, lng, self.default_prop_id)
        else:
            self.emit(f"红包豆 {left_dou} < {self.set_exchange_dou}，跳过兑换必中符")
        prop_id = self.query_props(token, lat, lng)
        if batch_id:
            # 11 点前默认不用必中符，节约道具（与原脚本 d_time7 逻辑一致）
            use_prop = prop_id if datetime.now().hour >= 11 else 1
            if use_prop != prop_id:
                self.emit("当前未到 11 点，暂不使用必中符")
            self.maybe_wait_big(token, lat, lng, use_prop)
            price = self.draw_lottery(token, lat, lng, batch_id, use_prop)
            self.accept_or_to_bean(token, lat, lng, batch_id, price)
        self.query_rewards(token)
        self.send_task_bean(token, lat, lng)
        self.query_beans(token, lat, lng)
        self.query_props(token, lat, lng)

    def run(self) -> None:
        self.initialize.info_message("美团天天神券开始")
        accounts = self.initialize.load_accounts()
        if not accounts:
            self.initialize.error_message(
                f"未配置账号。请设置 {self.env_name}=token "
                f"（从 https://h5.waimai.meituan.com Cookie 的 token 字段获取）"
            )
            return
        for index, (account_name, account) in enumerate(accounts, 1):
            self.initialize.info_message(f"共 {len(accounts)} 个账户，第 {index} 个：{account_name}")
            try:
                self.run_account(account_name, account)
            except Exception as exc:
                self.emit(f"{account_name} 执行失败：{exc}", ok=False)
            if index < len(accounts):
                delay = 2 + random.random() * 4
                self.initialize.info_message(f"等待 {delay:.1f}s 处理下一账号")
                time.sleep(delay)
        self.initialize.info_message("美团天天神券结束")
        self.initialize.send_notify("美团天天神券")


if __name__ == "__main__":
    MeituanShenquan().run()
