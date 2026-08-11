from __future__ import annotations

import time
import uuid

from .errors import ActionUnavailable, MemoryUnavailable, ModelUnavailable
from .intent import IntentRouter
from .schemas import ActionCommand, BrainRequest, BrainResponse, Diagnostics, Intent


class BrainCore:
    def __init__(self, context, models, memory_gateway, action_gateway, intent_router=None, persona="你是小乐。"):
        self.context, self.models = context, models
        self.memory_gateway, self.action_gateway = memory_gateway, action_gateway
        self.intent_router = intent_router or IntentRouter(getattr(models, "classify", None))
        self.persona = persona

    def respond(self, request: BrainRequest, user_id: str) -> BrainResponse:
        started, request_id = time.monotonic(), str(uuid.uuid4())
        conversation_id = self.context.resolve(user_id, request.conversation_id, request.message)
        history = self.context.history(user_id, conversation_id)
        decision = self.intent_router.classify(request.message, history, request_id)
        answer, sources, action = "", [], None
        model, fallback, gateway = "", False, None
        if decision.intent == Intent.MEMORY:
            gateway = "memory"
            try:
                result = self.memory_gateway.ask(request.message, history, request_id)
                answer, sources = result.answer.strip(), result.sources
            except MemoryUnavailable:
                answer = "乐知知识系统暂时不可用，我不能确认或补写相关资料，请稍后再试。"
        elif decision.intent == Intent.ACTION:
            gateway = "action"
            try:
                action = self.action_gateway.execute(ActionCommand.notification(conversation_id, request_id), request_id)
                answer = action.summary
            except ActionUnavailable:
                answer = "小可执行系统暂时不可用，测试通知没有确认成功。"
        else:
            try:
                result = self.models.complete(self.persona, [*history, {"role":"user","content":request.message}], request_id)
                answer, model, fallback = result.text, result.model, result.fallback
            except ModelUnavailable:
                answer = "模型服务暂时不可用，请稍后再试。"
        self.context.append_exchange(user_id, conversation_id, request.message, answer)
        return BrainResponse(
            request_id=request_id, conversation_id=conversation_id, intent=decision.intent, answer=answer,
            sources=sources, action=action,
            diagnostics=Diagnostics(model=model, gateway_used=gateway, latency_ms=max(0,int((time.monotonic()-started)*1000)), fallback=fallback),
        )
