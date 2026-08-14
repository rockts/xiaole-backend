from __future__ import annotations

from urllib.parse import quote

import requests

from ..errors import ReminderUnavailable
from ..schemas import ReminderCreateCommand, ReminderResult


class ReminderGateway:
    def __init__(self, base_url: str, token: str, timeout: float = 10, transport=None):
        self.base_url, self.token, self.timeout = base_url.rstrip("/"), token, timeout
        self.transport = transport or requests.Session()

    def create(self, command: ReminderCreateCommand, request_id: str) -> ReminderResult:
        body = self._request("POST", "/v1/reminders", request_id, json=command.action_core_payload())
        return self._project(body.get("reminder"))

    def list(self, filters: dict[str, str], request_id: str) -> list[ReminderResult]:
        body = self._request("GET", "/v1/reminders", request_id, params={key: value for key, value in filters.items() if value})
        rows = body.get("reminders")
        if not isinstance(rows, list):
            raise ReminderUnavailable("reminder service unavailable")
        return [self._project(row) for row in rows]

    def get(self, reminder_id: str, request_id: str) -> ReminderResult:
        return self._one("GET", reminder_id, None, request_id)

    def confirm(self, reminder_id: str, request_id: str) -> ReminderResult:
        return self._one("POST", reminder_id, "confirm", request_id)

    def pause(self, reminder_id: str, request_id: str) -> ReminderResult:
        return self._one("POST", reminder_id, "pause", request_id)

    def cancel(self, reminder_id: str, request_id: str) -> ReminderResult:
        return self._one("POST", reminder_id, "cancel", request_id)

    def _one(self, method: str, reminder_id: str, action: str | None, request_id: str) -> ReminderResult:
        path = f"/v1/reminders/{quote(reminder_id, safe='')}" + (f"/{action}" if action else "")
        return self._project(self._request(method, path, request_id).get("reminder"))

    def _request(self, method: str, path: str, request_id: str, **kwargs) -> dict:
        if not self.base_url or not self.token:
            raise ReminderUnavailable("reminder service unavailable")
        kwargs.update(headers={"Authorization": f"Bearer {self.token}", "X-Request-ID": request_id}, timeout=self.timeout)
        try:
            response = getattr(self.transport, method.lower())(self.base_url + path, **kwargs)
            if response.status_code not in (200, 202):
                raise ReminderUnavailable("reminder service unavailable")
            body = response.json()
            if not isinstance(body, dict):
                raise ReminderUnavailable("reminder service unavailable")
            return body
        except ReminderUnavailable:
            raise
        except Exception:
            raise ReminderUnavailable("reminder service unavailable") from None

    @staticmethod
    def _project(value) -> ReminderResult:
        if not isinstance(value, dict):
            raise ReminderUnavailable("reminder service unavailable")
        try:
            return ReminderResult.model_validate({key: value.get(key) for key in ReminderResult.model_fields})
        except Exception:
            raise ReminderUnavailable("reminder service unavailable") from None
