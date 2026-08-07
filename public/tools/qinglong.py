# -*- coding: utf-8 -*-
"""
青龙面板 Open API 公共封装。

与 notify / proxy 相同：不管前缀，只使用传入的配置（或环境变量名）。
前缀由 ImportSet.env_key / get_env 解析，例如：
  ImportSet("TX_LOGIN") → TX_LOGIN_client_id / TX_LOGIN_client_secret / TX_LOGIN_ql_url

也可直接传入已解析好的值构造 QingLongAPI(...)。

依赖：requests
"""
from __future__ import annotations

import os
from typing import Any, Callable

import requests


class QingLongAPI:
    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: int = 15,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = (base_url or "http://127.0.0.1:5700").rstrip("/")
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.timeout = timeout
        self._token: str | None = None
        self.session = session or requests.Session()
        self.session.headers.setdefault("Content-Type", "application/json")

    @staticmethod
    def read_env(config_name: str, default: str = "") -> str:
        """读取单个环境变量名（由 ImportSet.env_key 生成）。"""
        if not config_name:
            return default
        val = os.getenv(config_name)
        if val is not None and str(val).strip():
            return str(val).strip()
        return default

    @classmethod
    def from_env(
        cls,
        *,
        url_key: str = "QL_URL",
        id_key: str = "QL_CLIENT_ID",
        secret_key: str = "QL_CLIENT_SECRET",
        default_url: str = "http://127.0.0.1:5700",
        timeout: int = 15,
        session: requests.Session | None = None,
    ) -> "QingLongAPI":
        """
        只读传入的环境变量名（与 notify.read_config / proxy.get_proxy 一致）。
        url_key / id_key / secret_key 一般由 ImportSet.env_key 生成。
        """
        return cls(
            base_url=cls.read_env(url_key) or default_url,
            client_id=cls.read_env(id_key),
            client_secret=cls.read_env(secret_key),
            timeout=timeout,
            session=session,
        )

    @property
    def ready(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json",
        }

    def get_token(self) -> str:
        if self._token:
            return self._token
        if not self.ready:
            raise RuntimeError("未配置青龙 client_id / client_secret")
        resp = self.session.get(
            f"{self.base_url}/open/auth/token",
            params={"client_id": self.client_id, "client_secret": self.client_secret},
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"获取青龙 Token 失败: {data}")
        self._token = data["data"]["token"]
        self.session.headers["Authorization"] = f"Bearer {self._token}"
        return self._token

    def find_envs(self, name: str) -> list[dict[str, Any]]:
        self.get_token()
        resp = self.session.get(
            f"{self.base_url}/open/envs",
            headers=self._auth_headers(),
            params={"searchValue": name},
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"获取环境变量失败: {data}")
        return [env for env in (data.get("data") or []) if env.get("name") == name]

    def find_env(self, name: str) -> dict[str, Any] | None:
        envs = self.find_envs(name)
        return envs[0] if envs else None

    def delete_envs(self, ids: list[Any]) -> None:
        ids = [i for i in ids if i is not None]
        if not ids:
            return
        self.get_token()
        resp = self.session.delete(
            f"{self.base_url}/open/envs",
            headers=self._auth_headers(),
            json=ids,
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"删除环境变量失败: {data}")

    def enable_env(self, env: dict[str, Any]) -> None:
        if int(env.get("status") or 0) == 0:
            return
        self.get_token()
        resp = self.session.put(
            f"{self.base_url}/open/envs/enable",
            headers=self._auth_headers(),
            json=[env["id"]],
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"启用环境变量失败: {data}")

    def update_env(
        self,
        env: dict[str, Any],
        value: str,
        remarks: str | None = None,
    ) -> None:
        body = {
            "id": env["id"],
            "name": env["name"],
            "value": value,
            "remarks": remarks if remarks is not None else (env.get("remarks") or ""),
        }
        self.get_token()
        resp = self.session.put(
            f"{self.base_url}/open/envs",
            headers=self._auth_headers(),
            json=body,
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"更新环境变量失败: {data}")
        self.enable_env(env)

    def create_env(
        self,
        name: str,
        value: str,
        remarks: str = "",
    ) -> None:
        body = [{
            "name": name,
            "value": value,
            "remarks": remarks,
        }]
        self.get_token()
        resp = self.session.post(
            f"{self.base_url}/open/envs",
            headers=self._auth_headers(),
            json=body,
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("code") != 200:
            raise RuntimeError(f"创建环境变量失败: {data}")
        env = self.find_env(name)
        if env:
            self.enable_env(env)

    def set_env(
        self,
        name: str,
        value: str,
        *,
        merge: bool = False,
        merge_fn: Callable[[str, str], str] | None = None,
        remarks: str = "",
        dedupe: bool = True,
    ) -> dict[str, Any]:
        """
        写入环境变量。

        - 默认覆盖整段 value
        - merge=True 且提供 merge_fn(old, new) 时按回调合并
        - dedupe=True 时删除同名重复项，只保留第一条

        返回: {"action": "created"|"updated"|"merged", "deleted": int}
        """
        envs = self.find_envs(name)
        deleted = 0
        if not envs:
            self.create_env(name, value, remarks=remarks)
            return {"action": "created", "deleted": 0}

        keep, *dupes = envs
        if dedupe and dupes:
            self.delete_envs([e["id"] for e in dupes])
            deleted = len(dupes)

        if merge and merge_fn is not None:
            final = merge_fn(keep.get("value") or "", value)
            action = "merged"
        else:
            final = value
            action = "updated"
        self.update_env(keep, final, remarks=remarks or keep.get("remarks") or "")
        return {"action": action, "deleted": deleted}
