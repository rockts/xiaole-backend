from __future__ import annotations

from typing import Any

import requests


class LezhiHomeGateway:
    def __init__(self, base_url: str, token: str = "", timeout: float = 2.5, transport=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.transport = transport or requests.Session()

    def _get(self, path: str) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("knowledge service unavailable")
        headers = {"X-KOS-Token": self.token} if self.token else {}
        response = self.transport.get(f"{self.base_url}{path}", headers=headers, timeout=(1.0, self.timeout))
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise ValueError("invalid knowledge response")
        return value

    def intelligence(self): return self._get("/api/v1/status/intelligence")
    def knowledge(self): return self._get("/api/v1/status/knowledge")
    def profile(self): return self._get("/api/v1/profile")
    def profile_status(self): return self._get("/api/v1/profile/status")
