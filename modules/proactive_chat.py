"""
主动对话模块 - v0.5.0 Phase 5
让小乐能够主动发起对话，提升用户体验
"""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_setup import Message, UserBehavior, ProactiveQuestion, Memory
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv

load_dotenv()

# 数据库连接
if os.getenv('DATABASE_URL'):
    DB_URL = os.getenv('DATABASE_URL')
else:
    DB_URL = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
        f"/{os.getenv('DB_NAME')}"
    )

engine = create_engine(
    DB_URL,
    connect_args={'client_encoding': 'utf8'},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)


class ProactiveChat:
    """主动对话发起器"""

    def __init__(self):
        """初始化"""
        pass

    def should_initiate_chat(self, user_id="default_user"):
        """
        判断是否应该发起主动对话

        Returns:
            dict: {
                "should_chat": bool,
                "reason": str,
                "message": str,
                "priority": int (1-5, 5最高)
            }
        """
        session = SessionLocal()
        try:
            # 检查各种触发条件，按优先级返回

            # 1. 检查未回答的主动问答（优先级最高）
            result = self._check_pending_questions(session, user_id)
            if result["should_chat"]:
                return result

            # 2. 检查长时间未聊天
            result = self._check_inactive_period(session, user_id)
            if result["should_chat"]:
                return result

            # 3. 检查用户活跃时间（在用户通常活跃的时间主动问候）
            result = self._check_active_time(session, user_id)
            if result["should_chat"]:
                return result

            # 4. 检查有趣的记忆话题
            result = self._check_interesting_topics(session, user_id)
            if result["should_chat"]:
                return result

            return {
                "should_chat": False,
                "reason": "no_trigger",
                "message": "",
                "priority": 0
            }

        finally:
            session.close()

    def _check_pending_questions(self, session, user_id):
        """检查是否有待追问的问题"""
        from datetime import datetime

        # 查询最近24小时内未追问的问题
        time_threshold = datetime.now() - timedelta(hours=24)

        pending = session.query(ProactiveQuestion).filter(
            ProactiveQuestion.user_id == user_id,
            ProactiveQuestion.followup_asked.is_(False),
            ProactiveQuestion.created_at >= time_threshold
        ).order_by(ProactiveQuestion.confidence_score.desc()).first()

        if pending:
            # 构造自然的追问
            question = pending.original_question
            if len(question) > 50:
                question = question[:50] + "..."

            return {
                "should_chat": True,
                "reason": "pending_question",
                "message": f"之前你问过「{question}」，我一直在想这个问题，现在有些想法想和你聊聊 🤔",
                "priority": 5,
                "metadata": {
                    "question_id": pending.id,
                    "original_question": pending.original_question
                }
            }

        return {"should_chat": False}

    def _check_inactive_period(self, session, user_id):
        """检查用户是否长时间未聊天"""
        # 获取最后一条消息时间
        last_message = session.query(Message).filter(
            Message.session_id.in_(
                session.query(func.distinct(Message.session_id))
            )
        ).order_by(Message.created_at.desc()).first()

        if not last_message:
            return {"should_chat": False}

        days_inactive = (datetime.now() - last_message.created_at).days

        # 7天未聊天 -> 主动问候
        if days_inactive >= 7:
            greetings = [
                "好久不见！最近怎么样？ 😊",
                "嗨！有段时间没聊天了，想你了～",
                "Hello！最近忙吗？有什么新鲜事想分享吗？",
            ]

            # 根据星期选择不同的问候
            weekday = datetime.now().weekday()
            message = greetings[weekday % len(greetings)]

            return {
                "should_chat": True,
                "reason": "long_inactive",
                "message": message,
                "priority": 4,
                "metadata": {
                    "days_inactive": days_inactive
                }
            }

        # 3天未聊天 -> 轻度问候
        elif days_inactive >= 3:
            return {
                "should_chat": True,
                "reason": "moderate_inactive",
                "message": "最近还好吗？有什么我可以帮助的吗？ 💭",
                "priority": 3,
                "metadata": {
                    "days_inactive": days_inactive
                }
            }

        return {"should_chat": False}

    def _check_active_time(self, session, user_id):
        """检查是否是用户的活跃时间"""
        from datetime import datetime

        # 查询用户的活跃时间模式
        time_threshold = datetime.now() - timedelta(days=30)

        behaviors = session.query(UserBehavior).filter(
            UserBehavior.user_id == user_id,
            UserBehavior.created_at >= time_threshold
        ).all()

        if not behaviors:
            return {"should_chat": False}

        # 统计用户常在哪个小时段活跃
        hour_counts = {}
        for behavior in behaviors:
            hour = behavior.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        current_hour = datetime.now().hour

        # 如果当前是用户的高频活跃时间，且最近1小时内没有聊天
        if current_hour in hour_counts and hour_counts[current_hour] >= 3:
            last_hour_messages = session.query(Message).filter(
                Message.created_at >= datetime.now() - timedelta(hours=1)
            ).count()

            if last_hour_messages == 0:
                time_greetings = {
                    range(6, 9): "早上好！新的一天开始了 ☀️",
                    range(9, 12): "上午好！工作进展如何？",
                    range(12, 14): "午好！吃饭了吗？",
                    range(14, 18): "下午好！需要聊聊天放松一下吗？",
                    range(18, 22): "晚上好！今天过得怎么样？ 🌙",
                    range(22, 24): "还没休息吗？要早点睡哦～"
                }

                for time_range, greeting in time_greetings.items():
                    if current_hour in time_range:
                        return {
                            "should_chat": True,
                            "reason": "active_time",
                            "message": greeting,
                            "priority": 2,
                            "metadata": {
                                "hour": current_hour,
                                "activity_count": hour_counts[current_hour]
                            }
                        }

        return {"should_chat": False}

    def _check_interesting_topics(self, session, user_id):
        """检查是否有有趣的话题可以聊"""
        # 查找最近的记忆，看是否有有趣的话题
        time_threshold = datetime.now() - timedelta(days=7)

        interesting_memories = session.query(Memory).filter(
            Memory.created_at >= time_threshold,
            Memory.tag == "facts"  # 事实类记忆更有讨论价值
        ).order_by(Memory.created_at.desc()).limit(5).all()

        if not interesting_memories:
            return {"should_chat": False}

        # 随机选择一个记忆话题
        import random
        memory = random.choice(interesting_memories)

        # 构造基于记忆的对话开场
        content = memory.content
        if len(content) > 50:
            content = content[:50] + "..."

        topic_starters = [
            f"想起了你之前说的「{content}」，我觉得挺有意思的，想听听你现在的看法 🤔",
            f"关于「{content}」这个话题，我有些新的想法想和你探讨一下",
            f"你还记得我们聊过「{content}」吗？我一直在思考这个问题",
        ]

        return {
            "should_chat": True,
            "reason": "interesting_topic",
            "message": random.choice(topic_starters),
            "priority": 2,
            "metadata": {
                "memory_id": memory.id,
                "memory_content": memory.content
            }
        }

    def mark_chat_initiated(self, user_id, reason, message):
        """
        记录主动对话已发起

        Args:
            user_id: 用户ID
            reason: 触发原因
            message: 发送的消息
        """
        session = SessionLocal()
        try:
            # 如果是主动问答相关，标记已追问
            if reason == "pending_question":
                # 这个逻辑会在实际发送后处理
                pass

            # 可以记录到专门的表中，用于统计和避免过度打扰
            # 暂时先不实现，后续可以添加 proactive_chat_history 表

        finally:
            session.close()

    def get_chat_statistics(self, user_id="default_user", days=30):
        """
        获取主动对话统计

        Returns:
            dict: 主动对话统计数据
        """
        session = SessionLocal()
        try:
            time_threshold = datetime.now() - timedelta(days=days)

            # 统计最近的消息活动
            message_count = session.query(func.count(Message.id)).filter(
                Message.created_at >= time_threshold
            ).scalar()

            # 统计待追问的问题数
            pending_count = session.query(func.count(ProactiveQuestion.id)).filter(
                ProactiveQuestion.user_id == user_id,
                ProactiveQuestion.followup_asked.is_(False)
            ).scalar()

            # 获取最后活动时间
            last_message = session.query(Message).order_by(
                Message.created_at.desc()
            ).first()

            days_since_last = None
            if last_message:
                days_since_last = (
                    datetime.now() - last_message.created_at).days

            return {
                "message_count_30d": message_count,
                "pending_questions": pending_count,
                "days_since_last_chat": days_since_last,
                "should_initiate": days_since_last and days_since_last >= 3
            }

        finally:
            session.close()


# 全局单例
_proactive_chat = None


def get_proactive_chat():
    """获取ProactiveChat单例"""
    global _proactive_chat
    if _proactive_chat is None:
        _proactive_chat = ProactiveChat()
    return _proactive_chat
