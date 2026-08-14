from collections.abc import Callable

from .schemas import Intent, IntentDecision


def is_current_employment_query(message: str) -> bool:
    text = "".join(message.strip().lower().split())
    current = any(word in text for word in ("现在", "目前", "当前"))
    school = "学校" in text
    employment = any(word in text for word in ("工作", "工作单位", "任职", "就职"))
    location_question = any(word in text for word in ("在哪", "哪里", "哪儿", "是哪", "叫什么"))
    return location_question and ((current and (school or employment)) or school or (current and employment))


class IntentRouter:
    def __init__(self, classifier: Callable | None = None):
        self.classifier = classifier

    def classify(self, message: str, history: list[dict], request_id: str) -> IntentDecision:
        text = message.strip().lower()
        if "提醒" in text and any(word in text for word in ("创建", "查询", "列出", "查看", "详情", "确认", "暂停", "取消", "还款", "工作", "日常")):
            return IntentDecision(intent=Intent.REMINDER, reason_code="reminder_request")
        if any(word in text for word in ("手机发", "发一条测试通知", "发送测试通知")):
            return IntentDecision(intent=Intent.ACTION, reason_code="notification_request")
        if any(word in text for word in ("今天我最应该关注", "今天最应该关注", "今天有什么值得关注")):
            return IntentDecision(intent=Intent.STATUS, reason_code="today_priority")
        if any(word in text for word in ("值得写", "公众号选题", "写什么内容")):
            return IntentDecision(intent=Intent.PLANNING, reason_code="content_ideas")
        if is_current_employment_query(text):
            return IntentDecision(intent=Intent.KNOWLEDGE, reason_code="current_employment")
        if any(word in text for word in ("得过奖", "获过奖", "现在在哪", "当前学校", "现在的学校")):
            return IntentDecision(intent=Intent.KNOWLEDGE, reason_code="personal_fact")
        if any(word in text for word in ("官方通知", "官方文件", "知识库", "以前记录", "长期知识")):
            return IntentDecision(intent=Intent.KNOWLEDGE, reason_code="knowledge_query")
        if any(word in text for word in ("你好", "您好", "hello", "hi", "今天我们做什么")):
            return IntentDecision(intent=Intent.CONVERSATION, reason_code="conversation_rule")
        if self.classifier:
            try:
                value = self.classifier(message, history, request_id)
                return IntentDecision(intent=Intent(value), reason_code="model_fallback", used_fallback=True)
            except (ValueError, TypeError):
                pass
        return IntentDecision(intent=Intent.CONVERSATION, reason_code="safe_default", used_fallback=bool(self.classifier))
