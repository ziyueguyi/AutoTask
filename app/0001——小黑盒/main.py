"""
cron: 0 8 * * *
new Env("小黑盒签到")
"""

from __future__ import annotations

import os
from typing import List, Set

from loguru import logger

from notify import NotificationManager
from xiaoheihe import XiaoHeiHeDailyMission, resolve_request_mode_label


def load_env_file(path: str, override: bool = False) -> bool:
    if not path or not os.path.isfile(path):
        return False

    loaded_any = False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                if not key:
                    continue

                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]

                current_value = os.environ.get(key, "")
                if override or not (
                    isinstance(current_value, str) and current_value.strip()
                ):
                    os.environ[key] = value
                    loaded_any = True
    except OSError as exc:
        logger.warning(f"Failed to load env file {path}: {exc}")
        return False

    return loaded_any


def preload_env_files() -> List[str]:
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    candidates: List[str] = []
    env_file_hint = os.environ.get("XIAOHEIHE_ENV_FILE", "").strip() or os.environ.get(
        "LINUXDO_ENV_FILE", ""
    ).strip()
    if env_file_hint:
        candidates.append(env_file_hint)

    candidates.extend(
        [
            os.path.join(repo_dir, "xiaoheihe.env"),
            os.path.join(repo_dir, ".env"),
        ]
    )

    loaded_paths: List[str] = []
    seen_paths: Set[str] = set()
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        if load_env_file(normalized):
            loaded_paths.append(normalized)
    return loaded_paths


def env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name, default)
    return value.strip() if isinstance(value, str) else default


def env_bool(name: str, default: bool = False) -> bool:
    value = env_str(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = env_str(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"环境变量 {name} 不是有效整数: {value!r}，将回退到 {default}")
        return default


PRELOADED_ENV_FILES = preload_env_files()
if PRELOADED_ENV_FILES:
    logger.info("Preloaded env file(s): " + ", ".join(PRELOADED_ENV_FILES))

DEFAULT_IMPERSONATE = env_str("IMPERSONATE_VERSION", "chrome136") or "chrome136"

XIAOHEIHE_COOKIE = env_str("XIAOHEIHE_COOKIE") or env_str("XIAOHEIHE_COOKIES")
XIAOHEIHE_ENABLED = env_bool("XIAOHEIHE_ENABLED", bool(XIAOHEIHE_COOKIE))
XIAOHEIHE_ACCOUNT_NAME = env_str("XIAOHEIHE_ACCOUNT_NAME")
XIAOHEIHE_HEADERS_JSON = env_str("XIAOHEIHE_HEADERS_JSON")
XIAOHEIHE_REQUEST_MODE = env_str("XIAOHEIHE_REQUEST_MODE", "signer") or "signer"
XIAOHEIHE_TIMEOUT = env_int("XIAOHEIHE_TIMEOUT", 20)
XIAOHEIHE_RETRY_TIMES = env_int("XIAOHEIHE_RETRY_TIMES", 6)
XIAOHEIHE_RETRY_MIN_DELAY = env_int("XIAOHEIHE_RETRY_MIN_DELAY", 3)
XIAOHEIHE_RETRY_MAX_DELAY = env_int("XIAOHEIHE_RETRY_MAX_DELAY", 12)
XIAOHEIHE_IMPERSONATE = (
    env_str("XIAOHEIHE_IMPERSONATE", DEFAULT_IMPERSONATE) or DEFAULT_IMPERSONATE
)


def run() -> None:
    if not (XIAOHEIHE_ENABLED and XIAOHEIHE_COOKIE):
        print("请设置环境变量 XIAOHEIHE_COOKIE（需包含 pkey 与 x_xhh_tokenid）")
        raise SystemExit(1)

    if not env_str("XIAOHEIHE_KEY"):
        print("请设置环境变量 XIAOHEIHE_KEY（用于解密本地签名常量）")
        raise SystemExit(1)

    logger.info(
        "Xiaoheihe mode: "
        + resolve_request_mode_label(XIAOHEIHE_REQUEST_MODE)
    )
    ok = XiaoHeiHeDailyMission(
        notifier=NotificationManager(),
        account_name=XIAOHEIHE_ACCOUNT_NAME,
        cookie=XIAOHEIHE_COOKIE,
        headers_json=XIAOHEIHE_HEADERS_JSON,
        timeout=XIAOHEIHE_TIMEOUT,
        max_retries=XIAOHEIHE_RETRY_TIMES,
        retry_min_delay=XIAOHEIHE_RETRY_MIN_DELAY,
        retry_max_delay=XIAOHEIHE_RETRY_MAX_DELAY,
        impersonate=XIAOHEIHE_IMPERSONATE,
    ).run()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    run()
