"""
用户行为分析模块 - v0.3.0 Learning层
功能：
1. 收集用户对话行为数据
2. 分析对话模式（活跃时间、话题偏好）
3. 生成行为统计报告
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from collections import Counter
import json
import os
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


class BehaviorAnalyzer:
    """用户行为分析器"""

    def __init__(self):
        # 不再使用共享session，每个方法创建独立session
        pass

    def record_session_behavior(self, user_id, session_id):
        """
        记录单次会话的行为数据

        Args:
            user_id: 用户ID
            session_id: 会话ID
        """
        from db_setup import Message, UserBehavior

        # 创建独立session
        session = SessionLocal()
        try:
            # 查询会话消息
            messages = session.query(Message).filter(
                Message.session_id == session_id
            ).all()

            if not messages:
                return None

            # 统计数据
            user_messages = [m for m in messages if m.role == "user"]
            message_count = len(messages)
            user_message_count = len(user_messages)

            # 计算平均消息长度
            if user_messages:
                total_length = sum(len(m.content) for m in user_messages)
                avg_length = total_length // user_message_count
            else:
                avg_length = 0

            # 计算会话时长
            start_time = messages[0].created_at
            end_time = messages[-1].created_at
            duration = int((end_time - start_time).total_seconds())

            # 提取话题（从记忆标签中获取）
            # 简化版：从会话中提取关键词作为话题
            topics = self._extract_topics(user_messages)

            # v0.8.2: 新增情感分析和交互类型判断
            sentiment_score = self._analyze_sentiment(user_messages)
            interaction_type = self._determine_interaction_type(user_messages)

            # 检查是否已存在记录
            existing = session.query(UserBehavior).filter(
                UserBehavior.session_id == session_id
            ).first()

            if existing:
                # 更新现有记录
                existing.message_count = message_count
                existing.user_message_count = user_message_count
                existing.avg_message_length = avg_length
                existing.end_time = end_time
                existing.duration_seconds = duration
                existing.topics = json.dumps(topics, ensure_ascii=False)
                existing.sentiment_score = sentiment_score
                existing.interaction_type = interaction_type
            else:
                # 创建新记录
                behavior = UserBehavior(
                    user_id=user_id,
                    session_id=session_id,
                    message_count=message_count,
                    user_message_count=user_message_count,
                    avg_message_length=avg_length,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    topics=json.dumps(topics, ensure_ascii=False),
                    sentiment_score=sentiment_score,
                    interaction_type=interaction_type
                )
                session.add(behavior)

            session.commit()
            return {
                "session_id": session_id,
                "message_count": message_count,
                "duration": duration,
                "topics": topics,
                "sentiment_score": sentiment_score,
                "interaction_type": interaction_type
            }
        except Exception as e:
            session.rollback()
            print(f"Error recording behavior: {e}")
            return None
        finally:
            session.close()

    def _analyze_sentiment(self, messages):
        """
        简单情感分析 (基于关键词)
        Returns: float (-1.0 to 1.0)
        """
        positive_words = {"喜欢", "开心", "谢谢", "不错", "好",
                          "棒", "优秀", "爱", "快乐", "赞", "哈哈", "有趣"}
        negative_words = {"讨厌", "生气", "差", "坏", "难过",
                          "悲伤", "滚", "垃圾", "烦", "慢", "笨", "无聊"}

        score = 0.0
        count = 0

        for msg in messages:
            text = msg.content
            for word in positive_words:
                if word in text:
                    score += 0.5
            for word in negative_words:
                if word in text:
                    score -= 0.5
            count += 1

        # Normalize to -1 to 1
        if count == 0:
            return 0.0

        # 简单的归一化逻辑
        final_score = max(min(score, 1.0), -1.0)
        return round(final_score, 2)

    def _determine_interaction_type(self, messages):
        """
        判断交互类型: chat, task, qa
        """
        task_keywords = {"提醒", "闹钟", "日程", "待办",
                         "搜索", "查找", "播放", "打开", "计算", "帮我"}
        qa_keywords = {"是什么", "为什么", "怎么", "如何", "解释", "介绍", "谁", "哪里", "什么时候"}

        task_score = 0
        qa_score = 0

        for msg in messages:
            text = msg.content
            if any(k in text for k in task_keywords):
                task_score += 1
            if any(k in text for k in qa_keywords):
                qa_score += 1

        if task_score > 0:
            return "task"
        elif qa_score > 0:
            return "qa"
        else:
            return "chat"

    def _extract_topics(self, messages, top_n=5):
        """
        从消息中提取话题关键词（智能版）

        Args:
            messages: 消息列表
            top_n: 返回前N个高频词

        Returns:
            话题列表
        """
        try:
            import jieba
            import jieba.analyse
        except ImportError:
            return []

        # 定义话题分类规则（基于关键词匹配）
        topic_rules = {
            "天气": [
                "天气", "下雨", "温度", "晴天", "阴天",
                "雨", "雪", "风", "带伞", "冷", "热"
            ],
            "电脑": [
                "电脑", "内存", "磁盘", "CPU", "空间",
                "使用率", "系统", "机器"
            ],
            "时间": ["时间", "几点", "现在", "今天", "明天", "日期"],
            "健康": ["健康", "身体", "锻炼", "睡眠", "疲劳", "运动"],
            "工作": ["工作", "上班", "项目", "任务", "会议", "deadline"],
            "学习": ["学习", "课程", "知识", "教程", "书", "阅读"],
            "娱乐": ["电影", "游戏", "音乐", "视频", "看", "玩"],
            "美食": ["吃", "饭", "餐", "菜", "食物", "美食", "饿"],
            "旅游": ["旅游", "旅行", "景点", "出去玩", "度假"],
            "购物": ["买", "购物", "价格", "商品", "网购"],
            "聊天": ["聊天", "说话", "对话", "交流"],
            "计算": ["计算", "多少", "几个", "算", "数量", "腿"],
        }

        # 合并所有用户消息
        text = " ".join([m.content for m in messages])

        # 方法1: 基于规则匹配
        matched_topics = []
        for topic, keywords in topic_rules.items():
            for keyword in keywords:
                if keyword in text:
                    matched_topics.append(topic)
                    break

        # 方法2: jieba关键词提取（作为补充）
        jieba_keywords = jieba.analyse.extract_tags(text, topK=top_n * 2)

        # 过滤停用词和无意义词
        stopwords = {
            # 基础停用词
            "什么", "怎么", "怎么样", "吗", "呢", "啊",
            "的", "了", "是", "在", "有", "和",
            "我", "你", "他", "她", "它", "这", "那",
            # 扩展停用词（对话常见词）
            "喜欢", "你好", "认识", "可以", "知道", "告诉",
            "名字", "今年", "现在", "以前", "刚才", "时候",
            "所有", "关于", "尤其", "列表", "信息", "功能",
            "意思", "测试", "添加", "变化", "问答", "主动"
        }
        filtered_keywords = [
            k for k in jieba_keywords
            if k not in stopwords and len(k) > 1
        ]

        # 合并两种方法的结果，优先使用规则匹配
        topics = matched_topics + [
            k for k in filtered_keywords
            if k not in matched_topics
        ]

        # 去重并限制数量
        seen = set()
        result = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                result.append(topic)
                if len(result) >= top_n:
                    break

        return result if result else ["日常对话"]

    def get_user_activity_pattern(self, user_id, days=30):
        """
        获取用户活跃时间模式

        Args:
            user_id: 用户ID
            days: 统计最近N天

        Returns:
            {
                "hourly_distribution": {0: 5, 1: 2, ...},  # 按小时统计
                "daily_distribution": {0: 10, 1: 8, ...},  # 按星期统计
                "most_active_hour": 14,
                "most_active_day": "周三"
            }
        """
        from db_setup import UserBehavior

        session = SessionLocal()
        try:
            # 查询最近N天的行为记录
            since = datetime.now() - timedelta(days=days)
            behaviors = session.query(UserBehavior).filter(
                UserBehavior.user_id == user_id,
                UserBehavior.created_at >= since
            ).all()

            if not behaviors:
                return None

            # 按小时统计
            hourly = Counter()
            daily = Counter()

            for b in behaviors:
                hour = b.start_time.hour
                day = b.start_time.weekday()
                hourly[hour] += 1
                daily[day] += 1

            # 找出最活跃时段
            most_active_hour = hourly.most_common(1)[0][0] if hourly else None
            most_active_day = daily.most_common(1)[0][0] if daily else None

            day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

            return {
                "hourly_distribution": dict(hourly),
                "daily_distribution": dict(daily),
                "most_active_hour": most_active_hour,
                "most_active_day": day_names[most_active_day]
                if most_active_day is not None else None,
                "total_sessions": len(behaviors),
                "period_days": days
            }
        finally:
            session.close()

    def get_topic_preferences(self, user_id, days=30, top_n=10):
        """
        获取用户话题偏好

        Args:
            user_id: 用户ID
            days: 统计最近N天
            top_n: 返回前N个高频话题

        Returns:
            {
                "top_topics": [("话题1", 10), ("话题2", 8), ...],
                "total_topics": 50
            }
        """
        from db_setup import UserBehavior

        session = SessionLocal()
        try:
            # 查询最近N天的行为记录
            since = datetime.now() - timedelta(days=days)
            behaviors = session.query(UserBehavior).filter(
                UserBehavior.user_id == user_id,
                UserBehavior.created_at >= since
            ).all()

            if not behaviors:
                return None

            # 统计所有话题
            all_topics = []
            for b in behaviors:
                if b.topics:
                    try:
                        topics = json.loads(b.topics)
                        all_topics.extend(topics)
                    except json.JSONDecodeError:
                        continue

            topic_counts = Counter(all_topics)

            return {
                "top_topics": topic_counts.most_common(top_n),
                "total_topics": len(topic_counts),
                "period_days": days
            }
        finally:
            session.close()

    def get_conversation_stats(self, user_id, days=30):
        """
        获取对话统计数据

        Args:
            user_id: 用户ID
            days: 统计最近N天

        Returns:
            对话统计信息
        """
        from db_setup import UserBehavior

        session = SessionLocal()
        try:
            # 查询最近N天的行为记录
            since = datetime.now() - timedelta(days=days)
            behaviors = session.query(UserBehavior).filter(
                UserBehavior.user_id == user_id,
                UserBehavior.created_at >= since
            ).all()

            if not behaviors:
                return None

            total_sessions = len(behaviors)
            total_messages = sum(b.message_count for b in behaviors)
            total_user_messages = sum(b.user_message_count for b in behaviors)
            total_duration = sum(b.duration_seconds for b in behaviors)

            avg_messages_per_session = (
                total_messages // total_sessions if total_sessions > 0 else 0
            )
            avg_duration_per_session = (
                total_duration // total_sessions if total_sessions > 0 else 0
            )

            # 计算平均消息长度
            avg_lengths = [
                b.avg_message_length for b in behaviors
                if b.avg_message_length > 0
            ]
            overall_avg_length = (
                sum(avg_lengths) // len(avg_lengths) if avg_lengths else 0
            )

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "total_user_messages": total_user_messages,
                "avg_messages_per_session": avg_messages_per_session,
                "total_duration_minutes": total_duration // 60,
                "avg_duration_per_session_minutes": (
                    avg_duration_per_session // 60
                ),
                "avg_message_length": overall_avg_length,
                "period_days": days
            }
        finally:
            session.close()

    def get_advanced_stats(self, user_id, days=30):
        """
        获取高级统计数据 (情感趋势, 交互类型分布)
        """
        from db_setup import UserBehavior

        session = SessionLocal()
        try:
            since = datetime.now() - timedelta(days=days)
            behaviors = session.query(UserBehavior).filter(
                UserBehavior.user_id == user_id,
                UserBehavior.created_at >= since
            ).all()

            if not behaviors:
                return None

            # 情感趋势 (按天平均)
            sentiment_trend = {}
            for b in behaviors:
                date_str = b.start_time.strftime("%Y-%m-%d")
                if date_str not in sentiment_trend:
                    sentiment_trend[date_str] = []
                # 兼容旧数据 (None -> 0.0)
                score = b.sentiment_score if b.sentiment_score is not None else 0.0
                sentiment_trend[date_str].append(score)

            sentiment_daily = {
                k: round(sum(v)/len(v), 2) for k, v in sentiment_trend.items()
            }

            # 交互类型分布
            interaction_types = Counter([
                b.interaction_type if b.interaction_type else 'chat'
                for b in behaviors
            ])

            return {
                "sentiment_trend": sentiment_daily,
                "interaction_distribution": dict(interaction_types)
            }
        finally:
            session.close()

    def generate_behavior_report(self, user_id, days=30):
        """
        生成用户行为分析报告

        Args:
            user_id: 用户ID
            days: 统计最近N天

        Returns:
            完整的行为分析报告
        """
        return {
            "user_id": user_id,
            "report_date": datetime.now().isoformat(),
            "activity_pattern": self.get_user_activity_pattern(user_id, days),
            "topic_preferences": self.get_topic_preferences(user_id, days),
            "conversation_stats": self.get_conversation_stats(user_id, days)
        }
