# -*- coding: utf-8 -*-
"""淘系脚本统一请求间隔：每个 HTTP 请求后随机休眠 1～5 秒。"""
from __future__ import annotations

import random
import time
from typing import Callable


def sleep_after_request(
        tip: str = "",
        *,
        on_log: Callable[[str], None] | None = None,
) -> float:
    delay = random.uniform(1.0, 5.0)
    msg = f"{tip + ' ' if tip else ''}休眠 {delay:.1f}s"
    if on_log:
        on_log(msg)
    time.sleep(delay)
    return delay
