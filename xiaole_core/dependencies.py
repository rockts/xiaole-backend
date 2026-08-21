from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from db_setup import SessionLocal
from llm_gateway import get_llm_gateway

from .brain import BrainCore
from .context import CoreContextRepository
from .gateways.action import ActionGateway
from .gateways.reminder import ReminderGateway
from .gateways.memory import MemoryGateway
from .intent import IntentRouter
from .models import DeepSeekGatewayProvider, ModelRouter, OpenAICompatibleProvider
from .reminders import ReminderOrchestrator


@lru_cache(maxsize=1)
def build_brain_core() -> BrainCore:
    primary = DeepSeekGatewayProvider(get_llm_gateway())
    fallback = OpenAICompatibleProvider(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", os.getenv("QWEN_API_KEY", ""), os.getenv("QWEN_MODEL", "qwen-plus")
    )
    models = ModelRouter(primary, fallback)
    persona = (Path(__file__).with_name("persona.md")).read_text(encoding="utf-8").strip()
    memory = MemoryGateway(os.getenv("LEZHI_MEMORY_URL", "http://127.0.0.1:8765"), os.getenv("LEZHI_MEMORY_TOKEN", ""), float(os.getenv("LEZHI_MEMORY_TIMEOUT_SECONDS", "20")))
    action_url = os.getenv("XIAOKE_ACTION_URL", "")
    action_token = os.getenv("XIAOKE_API_TOKEN", "")
    action_timeout = float(os.getenv("XIAOKE_ACTION_TIMEOUT_SECONDS", "10"))
    action = ActionGateway(action_url, action_token, action_timeout)
    reminder = ReminderOrchestrator(ReminderGateway(action_url, action_token, action_timeout))
    return BrainCore(CoreContextRepository(SessionLocal), models, memory, action, IntentRouter(models.classify), persona, reminder_orchestrator=reminder)
