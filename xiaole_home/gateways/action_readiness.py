from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Readiness:
    status: str
    message: str


class ActionReadinessGateway:
    def __init__(self, base_url: str, token: str = "", timeout: float = 1.5, health_path: str = "/health", transport=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.health_path = health_path if health_path.startswith("/") else f"/{health_path}"
        self.transport = transport or requests.Session()

    def check(self) -> Readiness:
        if not self.base_url:
            return Readiness("unavailable", "行动服务状态暂时无法确认。")
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = self.transport.get(f"{self.base_url}{self.health_path}", headers=headers, timeout=self.timeout)
            if response.status_code < 200 or response.status_code >= 300:
                return Readiness("unavailable", "行动服务暂时不可用。")
            body = response.json()
            if not isinstance(body, dict):
                return Readiness("unavailable", "行动服务状态暂时无法确认。")
            raw = str(body.get("status") or body.get("health") or "").lower()
            if raw in {"ok", "healthy", "ready"}:
                return Readiness("healthy", "行动服务正常。")
            if raw in {"degraded", "partial"}:
                return Readiness("degraded", "行动服务部分能力暂不可用。")
            return Readiness("unavailable", "行动服务状态暂时无法确认。")
        except Exception:
            return Readiness("unavailable", "行动服务暂时不可用。")
