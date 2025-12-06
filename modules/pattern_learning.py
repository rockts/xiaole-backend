"""
模式学习模块 - v0.3.0 Learning层
功能：
1. 高频词汇识别
2. 同义词扩展学习
3. 常见问题自动归类
4. 用户偏好模型构建
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import re
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


class PatternLearner:
    """模式学习器"""

    def __init__(self):
        pass

    def learn_from_message(self, user_id, message_content, session_id):
        """
        从单条消息中学习模式

        Args:
            user_id: 用户ID
            message_content: 消息内容
            session_id: 会话ID
        """
        session = SessionLocal()
        try:
            # 提取词汇并学习高频词
            words = self._extract_words(message_content)
            self._learn_frequent_words(session, user_id, words)

            # 识别问题类型
            if self._is_question(message_content):
                self._learn_common_question(
                    session, user_id, message_content
                )

        finally:
            session.close()

    def _extract_words(self, text, min_length=2):
        """
        提取文本中的词汇

        Args:
            text: 文本内容
            min_length: 最小词长

        Returns:
            词汇列表
        """
        # 简单的中文分词（去除标点符号）
        words = re.findall(r'[\u4e00-\u9fa5]+', text)
        # 过滤短词
        return [w for w in words if len(w) >= min_length]

    def _is_question(self, text):
        """判断是否为问句"""
        question_markers = [
            '吗', '呢', '啊', '吧', '？', '?',
            '什么', '怎么', '为什么', '如何', '哪',
            '谁', '何时', '多少', '几'
        ]
        return any(marker in text for marker in question_markers)

    def _learn_frequent_words(self, session, user_id, words):
        """
        学习高频词汇

        Args:
            session: 数据库session
            user_id: 用户ID
            words: 词汇列表
        """
        from db_setup import LearnedPattern

        for word in words:
            # 查找是否已存在
            existing = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id,
                LearnedPattern.pattern_type == 'frequent_word',
                LearnedPattern.pattern_data.like(f'%"{word}"%')
            ).first()

            if existing:
                # 更新频次
                existing.frequency += 1
                existing.last_seen_at = datetime.now()
                # 根据频次调整置信度（最高95）
                existing.confidence = min(
                    50 + (existing.frequency * 2), 95
                )
            else:
                # 创建新记录
                pattern_data = json.dumps({
                    "word": word,
                    "context": []
                }, ensure_ascii=False)

                new_pattern = LearnedPattern(
                    user_id=user_id,
                    pattern_type='frequent_word',
                    pattern_data=pattern_data,
                    frequency=1,
                    confidence=50
                )
                session.add(new_pattern)

        session.commit()

    def _learn_common_question(self, session, user_id, question):
        """
        学习常见问题

        Args:
            session: 数据库session
            user_id: 用户ID
            question: 问题文本
        """
        from db_setup import LearnedPattern

        # 简单的问题分类（基于关键词）
        category = self._categorize_question(question)

        # 查找相似问题
        existing = session.query(LearnedPattern).filter(
            LearnedPattern.user_id == user_id,
            LearnedPattern.pattern_type == 'common_question',
            LearnedPattern.pattern_data.like(f'%{category}%')
        ).first()

        if existing:
            # 更新频次
            existing.frequency += 1
            existing.last_seen_at = datetime.now()
            existing.confidence = min(50 + (existing.frequency * 3), 95)

            # 更新问题列表
            data = json.loads(existing.pattern_data)
            if question not in data.get('examples', [])[:10]:
                if 'examples' not in data:
                    data['examples'] = []
                data['examples'].insert(0, question)
                data['examples'] = data['examples'][:10]  # 保留最近10个
                existing.pattern_data = json.dumps(
                    data, ensure_ascii=False
                )
        else:
            # 创建新记录
            pattern_data = json.dumps({
                "category": category,
                "examples": [question]
            }, ensure_ascii=False)

            new_pattern = LearnedPattern(
                user_id=user_id,
                pattern_type='common_question',
                pattern_data=pattern_data,
                frequency=1,
                confidence=50
            )
            session.add(new_pattern)

        session.commit()

    def _categorize_question(self, question):
        """
        问题分类

        Args:
            question: 问题文本

        Returns:
            分类名称
        """
        categories = {
            '天气查询': ['天气', '温度', '下雨', '晴', '阴'],
            '时间日期': ['几点', '什么时候', '日期', '时间', '今天', '明天'],
            '个人信息': ['年龄', '名字', '生日', '地址', '电话'],
            '功能咨询': ['怎么用', '如何', '功能', '能做', '可以'],
            '推荐建议': ['推荐', '建议', '什么好', '哪个好'],
            '闲聊': ['你好', '再见', '谢谢', '在吗', '干嘛']
        }

        for category, keywords in categories.items():
            if any(kw in question for kw in keywords):
                return category

        return '其他'

    def get_frequent_words(self, user_id, limit=20, min_frequency=3):
        """
        获取用户的高频词汇

        Args:
            user_id: 用户ID
            limit: 返回数量
            min_frequency: 最小频次

        Returns:
            高频词列表
        """
        from db_setup import LearnedPattern

        session = SessionLocal()
        try:
            patterns = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id,
                LearnedPattern.pattern_type == 'frequent_word',
                LearnedPattern.frequency >= min_frequency
            ).order_by(
                LearnedPattern.frequency.desc()
            ).limit(limit).all()

            results = []
            for p in patterns:
                data = json.loads(p.pattern_data)
                results.append({
                    'word': data.get('word'),
                    'frequency': p.frequency,
                    'confidence': p.confidence,
                    'last_seen': p.last_seen_at.isoformat()
                })

            return results
        finally:
            session.close()

    def get_common_questions(self, user_id, limit=10):
        """
        获取常见问题分类

        Args:
            user_id: 用户ID
            limit: 返回数量

        Returns:
            常见问题列表
        """
        from db_setup import LearnedPattern

        session = SessionLocal()
        try:
            patterns = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id,
                LearnedPattern.pattern_type == 'common_question'
            ).order_by(
                LearnedPattern.frequency.desc()
            ).limit(limit).all()

            results = []
            for p in patterns:
                data = json.loads(p.pattern_data)
                results.append({
                    'category': data.get('category'),
                    'frequency': p.frequency,
                    'confidence': p.confidence,
                    'examples': data.get('examples', [])[:3],
                    'last_seen': p.last_seen_at.isoformat()
                })

            return results
        finally:
            session.close()

    def get_learning_insights(self, user_id):
        """
        获取学习洞察

        Args:
            user_id: 用户ID

        Returns:
            学习洞察数据
        """
        from db_setup import LearnedPattern

        session = SessionLocal()
        try:
            # 统计各类模式数量
            total_patterns = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id
            ).count()

            frequent_words = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id,
                LearnedPattern.pattern_type == 'frequent_word'
            ).count()

            common_questions = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id,
                LearnedPattern.pattern_type == 'common_question'
            ).count()

            # 获取最高频模式
            top_pattern = session.query(LearnedPattern).filter(
                LearnedPattern.user_id == user_id
            ).order_by(
                LearnedPattern.frequency.desc()
            ).first()

            top_word = None
            if top_pattern and top_pattern.pattern_type == 'frequent_word':
                data = json.loads(top_pattern.pattern_data)
                top_word = {
                    'word': data.get('word'),
                    'frequency': top_pattern.frequency
                }

            return {
                'total_patterns': total_patterns,
                'frequent_words_count': frequent_words,
                'common_questions_count': common_questions,
                'top_word': top_word,
                'learning_active': total_patterns > 0
            }
        finally:
            session.close()
