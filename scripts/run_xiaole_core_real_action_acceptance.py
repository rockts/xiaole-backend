#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import requests

ROOT = Path(__file__).resolve().parents[1]
XIAOKE_ROOT = Path("/Users/rockts/Dev/xiaoke/xiaoke-action-core")
RUNTIME_DIR = ROOT / "runtime"
DATABASE_PATH = RUNTIME_DIR / "xiaoke-first-real-action.db"
FIXED_REQUEST_UUID = "c8fb3f33-3c4f-4f15-9b2e-8c6c9e9d2011"

sys.path.insert(0, str(ROOT))

from xiaole_core.brain import BrainCore
from xiaole_core.gateways.action import ActionGateway
from xiaole_core.schemas import BrainRequest


class EphemeralContext:
    def __init__(self): self.messages = []
    def resolve(self, _user, conversation_id, _message): return conversation_id or "xiaole-first-real-action"
    def history(self, _user, _conversation_id): return list(self.messages[-12:])
    def append_exchange(self, _user, _conversation_id, message, answer):
        self.messages.extend(({"role":"user","content":message},{"role":"assistant","content":answer}))


class UnusedModel:
    def complete(self, *_): raise AssertionError("action path must not call model")
    def classify(self, *_): return "action"


class ForbiddenMemoryGateway:
    calls = 0
    def ask(self, *_):
        self.calls += 1
        raise AssertionError("action path must not call Memory Gateway")


class CriticalAcceptanceGateway(ActionGateway):
    def execute(self, command, request_id):
        command.parameters["urgency"] = "critical"
        return super().execute(command, request_id)


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_ready(url: str, process: subprocess.Popen) -> None:
    for _ in range(100):
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError("local Action Core stopped before ready: " + output[-1000:])
        try:
            if requests.get(url + "/health", timeout=.2).status_code == 200:
                return
        except requests.RequestException:
            time.sleep(.05)
    raise RuntimeError("local Action Core did not become ready")


def remote_event(target: str, event_id: str) -> dict:
    code = (
        "import json,sqlite3,sys;"
        "db=sqlite3.connect('/mnt/data/workspace/projects/monitor-service/monitor.db');"
        "db.row_factory=sqlite3.Row;"
        "r=db.execute('SELECT event_id,status,delivery_status,attempts FROM notification_events WHERE event_id=?',(sys.argv[1],)).fetchone();"
        "print(json.dumps(dict(r) if r else {}))"
    )
    completed = subprocess.run(
        ["/usr/bin/ssh", "-o", "BatchMode=yes", "-o", "LogLevel=ERROR", target, "python3", "-c", code, event_id],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("remote notification evidence query failed")
    return json.loads(completed.stdout)


def main() -> int:
    monitor_token = os.environ.get("XIAOKE_NOTIFICATION_TOKEN", "")
    tunnel_target = os.environ.get("XIAOKE_SSH_TUNNEL_TARGET", "")
    local_port = os.environ.get("XIAOKE_SSH_LOCAL_PORT", "18080")
    if not monitor_token or not tunnel_target:
        raise RuntimeError("production notification bridge configuration is unavailable")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    action_port = free_port()
    action_token = "xiaole-first-real-action-local-token"
    action_url = f"http://127.0.0.1:{action_port}"
    env = os.environ.copy()
    env.update({
        "XIAOKE_API_TOKEN": action_token,
        "XIAOKE_DATABASE_PATH": str(DATABASE_PATH),
        "MONITOR_NOTIFICATION_URL": f"http://127.0.0.1:{local_port}/api/v2/notifications",
        "MONITOR_NOTIFICATION_TOKEN": monitor_token,
    })
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", str(action_port), "--log-level", "warning"],
        cwd=XIAOKE_ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        wait_ready(action_url, process)
        memory = ForbiddenMemoryGateway()
        gateway = CriticalAcceptanceGateway(action_url, action_token, timeout=20)
        brain = BrainCore(EphemeralContext(), UnusedModel(), memory, gateway)
        with patch("xiaole_core.brain.uuid.uuid4", return_value=FIXED_REQUEST_UUID):
            response = brain.respond(BrainRequest(message="给我手机发一条小乐 2.0 测试通知。"), "acceptance-user")
        task_id = response.action.task_id if response.action else ""
        task_response = requests.get(
            f"{action_url}/v1/tasks/{task_id}", headers={"Authorization":f"Bearer {action_token}"}, timeout=5,
        )
        task_response.raise_for_status()
        task = task_response.json()["task"]
        attempts = task.get("attempts") or []
        attempt = attempts[0] if attempts else {}
        evidence = attempt.get("evidence") or {}
        event = remote_event(tunnel_target, str(evidence.get("downstream_event_id") or ""))
        serialized = response.model_dump_json()
        forbidden_values = [monitor_token, action_token, "monitor-service", "BARK_KEY", "api.day.app"]
        report = {
            "input": "给我手机发一条小乐 2.0 测试通知。",
            "intent": response.intent.value,
            "memory_gateway_calls": memory.calls,
            "task_id": task_id,
            "task_status": task.get("status"),
            "task_type": task.get("task_type"),
            "title_matches": task.get("parameters",{}).get("title") == "【小乐 2.0】",
            "body_matches": task.get("parameters",{}).get("body") == "小乐已成功通过小可完成首次真实 Action。",
            "execution_attempt_count": len(attempts),
            "execution_outcome": attempt.get("outcome"),
            "notification_event_id": event.get("event_id"),
            "notification_status": event.get("status"),
            "delivery_status": event.get("delivery_status"),
            "bark_call_count": event.get("attempts"),
            "brain_answer": response.answer,
            "response_evidence": response.action.evidence if response.action else {},
            "response_secret_free": not any(value and value in serialized for value in forbidden_values),
            "production_bridge": True,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        required = (
            report["intent"] == "action" and report["memory_gateway_calls"] == 0
            and report["task_status"] == "success" and report["task_type"] == "notification.send"
            and report["title_matches"] and report["body_matches"]
            and report["execution_attempt_count"] == 1 and report["execution_outcome"] == "success"
            and report["notification_status"] == "accepted" and report["delivery_status"] == "sent"
            and report["bark_call_count"] == 1 and report["response_secret_free"]
        )
        return 0 if required else 1
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
