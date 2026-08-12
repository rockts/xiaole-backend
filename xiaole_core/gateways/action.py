from __future__ import annotations

import time
from datetime import datetime, timezone

import requests

from ..errors import ActionUnavailable
from ..schemas import ActionCommand, ActionResult


class ActionGateway:
    TERMINAL = {"success", "failed", "cancelled", "dead"}

    def __init__(self, base_url: str, token: str, timeout: float = 10, poll_interval: float = .1, transport=None, sleeper=time.sleep):
        self.base_url, self.token, self.timeout, self.poll_interval = base_url.rstrip("/"), token, timeout, poll_interval
        self.transport, self.sleeper = transport or requests.Session(), sleeper

    def execute(self, command: ActionCommand, request_id: str) -> ActionResult:
        if not self.base_url:
            raise ActionUnavailable("action system unavailable")
        headers = {"Authorization": f"Bearer {self.token}", "X-Request-ID": request_id}
        payload = {
            "idempotency_key": f"xiaole:{request_id}:{command.task_type}", "source_system":"xiaole", "task_type":command.task_type,
            "priority":"normal", "target":{"channel":"mobile"}, "parameters":command.parameters, "risk_level":"low",
            "requires_confirmation":False, "confirmation_token":"", "requested_at":datetime.now(timezone.utc).isoformat(),
            "metadata":{"conversation_id":command.conversation_id,"request_id":request_id},
        }
        try:
            created = self.transport.post(f"{self.base_url}/v1/tasks", json=payload, headers=headers, timeout=self.timeout)
            if created.status_code not in (200, 202): raise ActionUnavailable("action task creation failed")
            task_id = created.json()["task"]["task_id"]
            max_polls = max(1, int(self.timeout / max(self.poll_interval, .001)))
            for _ in range(max_polls):
                response = self.transport.get(f"{self.base_url}/v1/tasks/{task_id}", headers=headers, timeout=self.timeout)
                if response.status_code != 200: raise ActionUnavailable("action task query failed")
                task = response.json()["task"]
                status = task["status"]
                if status in self.TERMINAL:
                    evidence = {"execution_confirmed": status == "success"}
                    summary = "测试通知任务已由小可成功执行。" if status == "success" else f"测试通知任务未完成，状态为 {status}。"
                    return ActionResult(task_id=task_id,status=status,summary=summary,evidence=evidence,request_id=request_id)
                self.sleeper(self.poll_interval)
            return ActionResult(task_id=task_id,status="timeout",summary="通知已受理，正在等待发送；当前尚不能确认发送成功。",request_id=request_id)
        except ActionUnavailable:
            raise
        except Exception as exc:
            raise ActionUnavailable("action system unavailable") from exc
