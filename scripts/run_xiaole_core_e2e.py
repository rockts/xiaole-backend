#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xiaole_core.brain import BrainCore
from xiaole_core.gateways.action import ActionGateway
from xiaole_core.gateways.memory import MemoryGateway
from xiaole_core.schemas import BrainRequest


class EphemeralContext:
    def __init__(self): self.history_by_id = {}
    def resolve(self, _user, cid, _message):
        cid = cid or "e2e-conversation"; self.history_by_id.setdefault(cid, []); return cid
    def history(self, _user, cid): return list(self.history_by_id[cid][-12:])
    def append_exchange(self, _user, cid, message, answer): self.history_by_id[cid] += [{"role":"user","content":message},{"role":"assistant","content":answer}]


class DeterministicModel:
    calls = 0
    def complete(self, *_):
        self.calls += 1
        return type("Result", (), {"text":"你好。我们可以先确认今天最重要的一件事。","model":"e2e-local","fallback":False})()
    def classify(self, *_): return "conversation"


class CountingGateway:
    def __init__(self): self.calls=0
    def ask(self,*_): self.calls+=1; raise AssertionError("unexpected memory call")
    def execute(self,*_): self.calls+=1; raise AssertionError("unexpected action call")


def free_port():
    with socket.socket() as sock: sock.bind(("127.0.0.1",0)); return sock.getsockname()[1]


def conversation_e2e():
    model, memory, action = DeterministicModel(), CountingGateway(), CountingGateway()
    response = BrainCore(EphemeralContext(), model, memory, action).respond(BrainRequest(message="你好，今天我们做什么？"), "e2e")
    return {"intent":response.intent.value,"answer":response.answer,"memory_calls":memory.calls,"action_calls":action.calls,"production_connected":False,"bark_sent":False}


def memory_e2e():
    memory = MemoryGateway("http://127.0.0.1:8765", timeout=60)
    response = BrainCore(EphemeralContext(), DeterministicModel(), memory, CountingGateway()).respond(BrainRequest(message="最近有什么值得我关注的官方通知？"), "e2e")
    return {"intent":response.intent.value,"answer":response.answer,"sources":response.sources,"source_count":len(response.sources),"lezhi_url":"http://127.0.0.1:8765/ask","production_connected":False,"bark_sent":False}


class MockMonitor(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def do_POST(self):
        length=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(length)); event_id=body["event_id"]
        payload=json.dumps({"status":"accepted","event_id":event_id,"delivery_status":"sent","duplicate":False}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(payload))); self.end_headers(); self.wfile.write(payload)


def action_e2e():
    xiaoke_root=Path("/Users/rockts/Dev/xiaoke/xiaoke-action-core")
    if not xiaoke_root.exists(): raise RuntimeError("local Xiaoke checkout missing")
    monitor_port, action_port = free_port(), free_port()
    monitor=ThreadingHTTPServer(("127.0.0.1",monitor_port),MockMonitor); thread=threading.Thread(target=monitor.serve_forever,daemon=True); thread.start()
    with tempfile.TemporaryDirectory(prefix="xiaole-xiaoke-e2e-") as directory:
        env=os.environ.copy(); env.update({"XIAOKE_API_TOKEN":"xiaole-e2e-token","XIAOKE_DATABASE_PATH":str(Path(directory)/"action.db"),"MONITOR_NOTIFICATION_URL":f"http://127.0.0.1:{monitor_port}/v1/notifications","MONITOR_NOTIFICATION_TOKEN":"mock-only"})
        command=[sys.executable,"-m","uvicorn","app.main:create_app","--factory","--host","127.0.0.1","--port",str(action_port),"--log-level","warning"]
        process=subprocess.Popen(command,cwd=xiaoke_root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            for _ in range(100):
                if process.poll() is not None: raise RuntimeError("local Xiaoke stopped before ready: "+(process.stdout.read() if process.stdout else ""))
                try:
                    if requests.get(f"http://127.0.0.1:{action_port}/health",timeout=.2).status_code==200: break
                except requests.RequestException: time.sleep(.05)
            else: raise RuntimeError("local Xiaoke did not become ready")
            response=BrainCore(EphemeralContext(),DeterministicModel(),CountingGateway(),ActionGateway(f"http://127.0.0.1:{action_port}","xiaole-e2e-token",timeout=10)).respond(BrainRequest(message="给我手机发一条测试通知。"),"e2e")
            return {"intent":response.intent.value,"task_id":response.action.task_id if response.action else "","status":response.action.status if response.action else "","evidence":response.action.evidence if response.action else {},"mock_notification_downstream":True,"production_connected":False,"bark_sent":False}
        finally:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            monitor.shutdown(); monitor.server_close()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=("conversation","memory","action")); args=parser.parse_args()
    result={"conversation":conversation_e2e,"memory":memory_e2e,"action":action_e2e}[args.mode]()
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
