#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xiaole_core.gateways.reminder import ReminderGateway
from xiaole_core.schemas import ReminderCreateCommand


SHANGHAI = ZoneInfo("Asia/Shanghai")


def parser():
    root = argparse.ArgumentParser(description="XiaoLe unified reminder acceptance")
    root.add_argument("--execute", action="store_true", help="perform the external Action Core write")
    root.add_argument("--ack-observation", action="store_true", help="confirm Leke Insight was checked before cancellation")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    now = datetime.now(SHANGHAI).replace(second=0, microsecond=0)
    event_at, notify_at = now + timedelta(days=7), now + timedelta(days=6, hours=23)
    plan = {"mode":"execute" if args.execute else "dry-run", "title":"部署验收", "category":"work", "source_system":"xiaole",
            "event_at":event_at.isoformat(), "notify_at":notify_at.isoformat(), "will_cancel":True, "bark_direct_call":False}
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, separators=(",",":")))
        return 0
    if not args.ack_observation:
        print(json.dumps({"ok":False,"error":"ack-observation-required"}, separators=(",",":")))
        return 2
    gateway = ReminderGateway(os.getenv("XIAOKE_ACTION_URL", ""), os.getenv("XIAOKE_API_TOKEN", ""), float(os.getenv("XIAOKE_ACTION_TIMEOUT_SECONDS", "10")))
    created = None
    try:
        created = gateway.create(ReminderCreateCommand(
            idempotency_key=f"xiaole:deployment-acceptance:{uuid.uuid4()}", title="部署验收", category="work",
            event_at=event_at.isoformat(), notify_at=notify_at.isoformat(), notification_title="部署验收",
            notification_body="小乐统一提醒部署验收（非真实业务数据）", metadata={"channel":"xiaole-v2","purpose":"deployment-acceptance"}), "deployment-acceptance")
        stored = gateway.get(created.reminder_id, "deployment-acceptance-get")
        print(json.dumps({"created":created.model_dump(),"stored":stored.model_dump(),"observation_acknowledged":True}, ensure_ascii=False, separators=(",",":")))
        return 0
    finally:
        if created is not None:
            cancelled = gateway.cancel(created.reminder_id, "deployment-acceptance-cancel")
            print(json.dumps({"cancelled":{"reminder_id":cancelled.reminder_id,"status":cancelled.status}}, ensure_ascii=False, separators=(",",":")))


if __name__ == "__main__":
    raise SystemExit(main())
