"""
学习层模块 - v0.7.0
追踪用户知识进度、学习偏好和知识空白

核心功能：
1. 知识图谱：记录用户学到的知识点
2. 学习进度追踪：了解用户对某个主题的掌握程度
3. 学习偏好分析：识别用户的学习方式和兴趣
4. 知识推荐：基于学习历史推荐相关话题
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
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
    connect_args={'client_encoding': 'utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ====================
# 数据模型
# ====================
class KnowledgeNode(Base):
    """知识节点 - 用户学到的每个知识点"""
    __tablename__ = 'knowledge_nodes'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    topic = Column(String(255), nullable=False, index=True)  # 主题
    content = Column(Text, nullable=False)  # 知识点内容
    mastery_level = Column(Float, default=0.0)  # 掌握程度 0-1
    confidence = Column(Float, default=0.5)  # 置信度
    source_session_id = Column(String(255))  # 来源会话
    related_topics = Column(Text)  # 关联主题（JSON列表）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LearningProgress(Base):
    """学习进度 - 用户对某个主题的整体掌握情况"""
    __tablename__ = 'learning_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    topic = Column(String(255), nullable=False, index=True)
    total_knowledge_count = Column(Integer, default=0)
    mastered_count = Column(Integer, default=0)  # 掌握的知识点数
    avg_mastery_level = Column(Float, default=0.0)
    last_learned_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class LearningPreference(Base):
    """学习偏好 - 用户的学习方式和兴趣"""
    __tablename__ = 'learning_preferences'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    preferred_topics = Column(Text)  # 偏好主题（JSON列表）
    learning_style = Column(String(50))  # visual/auditory/kinesthetic
    depth_preference = Column(String(50))  # shallow/moderate/deep
    interaction_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ====================
# 学习管理器
# ====================
class LearningManager:
    """学习层管理器"""

    def __init__(self):
        self.session = SessionLocal()
        # 确保表存在
        Base.metadata.create_all(engine)

    def add_knowledge(
        self,
        user_id: str,
        topic: str,
        content: str,
        session_id: Optional[str] = None,
        mastery_level: float = 0.3,
        related_topics: Optional[List[str]] = None
    ) -> int:
        """
        添加新知识点

        Args:
            user_id: 用户ID
            topic: 主题（如"Python编程"、"咖啡知识"）
            content: 知识点内容
            session_id: 来源会话ID
            mastery_level: 初始掌握程度（默认0.3，表示初步了解）
            related_topics: 关联主题列表

        Returns:
            知识点ID
        """
        # 检查是否已存在相同知识点
        existing = self.session.query(KnowledgeNode).filter_by(
            user_id=user_id,
            topic=topic,
            content=content
        ).first()

        if existing:
            # 更新掌握程度（每次提到都增加）
            existing.mastery_level = min(
                existing.mastery_level + 0.1, 1.0
            )
            existing.updated_at = datetime.now()
            self.session.commit()

            # 更新进度
            self._update_progress(user_id, topic)
            return existing.id

        # 创建新知识点
        knowledge = KnowledgeNode(
            user_id=user_id,
            topic=topic,
            content=content,
            mastery_level=mastery_level,
            source_session_id=session_id,
            related_topics=json.dumps(related_topics or [],
                                      ensure_ascii=False)
        )
        self.session.add(knowledge)
        self.session.commit()

        # 更新进度
        self._update_progress(user_id, topic)

        return knowledge.id

    def _update_progress(self, user_id: str, topic: str):
        """更新学习进度"""
        # 统计该主题下的所有知识点
        knowledge_list = self.session.query(KnowledgeNode).filter_by(
            user_id=user_id,
            topic=topic
        ).all()

        if not knowledge_list:
            return

        total = len(knowledge_list)
        mastered = sum(1 for k in knowledge_list if k.mastery_level >= 0.7)
        avg_mastery = sum(k.mastery_level for k in knowledge_list) / total

        # 更新或创建进度记录
        progress = self.session.query(LearningProgress).filter_by(
            user_id=user_id,
            topic=topic
        ).first()

        if progress:
            progress.total_knowledge_count = total
            progress.mastered_count = mastered
            progress.avg_mastery_level = avg_mastery
            progress.last_learned_at = datetime.now()
        else:
            progress = LearningProgress(
                user_id=user_id,
                topic=topic,
                total_knowledge_count=total,
                mastered_count=mastered,
                avg_mastery_level=avg_mastery,
                last_learned_at=datetime.now()
            )
            self.session.add(progress)

        self.session.commit()

    def get_knowledge_gaps(
        self,
        user_id: str,
        topic: Optional[str] = None
    ) -> List[Dict]:
        """
        获取知识空白（掌握程度低的知识点）

        Returns:
            [
                {
                    'topic': str,
                    'content': str,
                    'mastery_level': float,
                    'gap_score': float  # 空白程度（1-mastery_level）
                }
            ]
        """
        query = self.session.query(KnowledgeNode).filter_by(user_id=user_id)

        if topic:
            query = query.filter_by(topic=topic)

        # 找出掌握程度<0.5的知识点
        gaps = query.filter(KnowledgeNode.mastery_level < 0.5).all()

        result = []
        for gap in gaps:
            result.append({
                'topic': gap.topic,
                'content': gap.content,
                'mastery_level': gap.mastery_level,
                'gap_score': 1.0 - gap.mastery_level,
                'last_updated': gap.updated_at.isoformat()
            })

        # 按空白程度排序
        result.sort(key=lambda x: x['gap_score'], reverse=True)
        return result

    def get_learning_progress(
        self,
        user_id: str,
        topic: Optional[str] = None
    ) -> List[Dict]:
        """
        获取学习进度报告

        Returns:
            [
                {
                    'topic': str,
                    'total_knowledge': int,
                    'mastered': int,
                    'progress': float,  # 0-100%
                    'avg_mastery': float,
                    'last_learned': str
                }
            ]
        """
        query = self.session.query(LearningProgress).filter_by(
            user_id=user_id
        )

        if topic:
            query = query.filter_by(topic=topic)

        progress_list = query.all()

        result = []
        for p in progress_list:
            progress_pct = (
                (p.mastered_count / p.total_knowledge_count * 100)
                if p.total_knowledge_count > 0 else 0
            )
            result.append({
                'topic': p.topic,
                'total_knowledge': p.total_knowledge_count,
                'mastered': p.mastered_count,
                'progress': round(progress_pct, 1),
                'avg_mastery': round(p.avg_mastery_level, 2),
                'last_learned': (
                    p.last_learned_at.isoformat()
                    if p.last_learned_at else None
                )
            })

        return result

    def recommend_topics(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        推荐相关话题（基于已学知识）

        Returns:
            [
                {
                    'topic': str,
                    'reason': str,
                    'relevance': float
                }
            ]
        """
        # 获取用户的知识节点
        knowledge_list = self.session.query(KnowledgeNode).filter_by(
            user_id=user_id
        ).all()

        if not knowledge_list:
            return []

        # 提取所有关联主题
        related_topics_count = {}
        for k in knowledge_list:
            if k.related_topics:
                try:
                    topics = json.loads(k.related_topics)
                    for topic in topics:
                        related_topics_count[topic] = (
                            related_topics_count.get(topic, 0) + 1
                        )
                except:
                    pass

        # 排除已经学习的主题
        learned_topics = set(k.topic for k in knowledge_list)

        recommendations = []
        for topic, count in related_topics_count.items():
            if topic not in learned_topics:
                recommendations.append({
                    'topic': topic,
                    'reason': f'与你已学的{count}个知识点相关',
                    'relevance': count / len(knowledge_list)
                })

        # 按相关度排序
        recommendations.sort(key=lambda x: x['relevance'], reverse=True)
        return recommendations[:limit]

    def detect_learning_plateau(
        self,
        user_id: str,
        topic: str,
        days: int = 7
    ) -> Tuple[bool, str]:
        """
        检测学习平台期（长时间无进步）

        Returns:
            (是否进入平台期, 原因)
        """
        # 获取该主题的进度
        progress = self.session.query(LearningProgress).filter_by(
            user_id=user_id,
            topic=topic
        ).first()

        if not progress:
            return False, ""

        # 检查最近是否有学习
        if progress.last_learned_at:
            days_since_last = (
                datetime.now() - progress.last_learned_at
            ).days

            if days_since_last > days:
                return True, f"已经{days_since_last}天没有学习{topic}了"

        # 检查是否掌握程度停滞
        if progress.avg_mastery_level < 0.5 and progress.total_knowledge_count > 5:
            return True, f"{topic}掌握程度偏低（{progress.avg_mastery_level:.0%}）"

        return False, ""

    def close(self):
        """关闭会话"""
        self.session.close()


# ====================
# 全局实例
# ====================
_learning_manager_instance = None


def get_learning_manager() -> LearningManager:
    """获取学习管理器单例"""
    global _learning_manager_instance
    if _learning_manager_instance is None:
        _learning_manager_instance = LearningManager()
    return _learning_manager_instance


# ====================
# 测试代码
# ====================
if __name__ == "__main__":
    # 测试学习层功能
    lm = LearningManager()

    # 添加一些测试数据
    print("=" * 60)
    print("测试1: 添加知识点")
    lm.add_knowledge(
        user_id="test_user",
        topic="Python编程",
        content="Python使用缩进来表示代码块",
        mastery_level=0.6,
        related_topics=["编程基础", "代码规范"]
    )
    lm.add_knowledge(
        user_id="test_user",
        topic="Python编程",
        content="列表推导式是一种简洁的创建列表的方法",
        mastery_level=0.3
    )
    print("✅ 知识点已添加")

    print("\n" + "=" * 60)
    print("测试2: 查询学习进度")
    progress = lm.get_learning_progress("test_user")
    for p in progress:
        print(f"主题: {p['topic']}")
        print(f"进度: {p['progress']}%")
        print(f"已掌握: {p['mastered']}/{p['total_knowledge']}")
        print(f"平均掌握度: {p['avg_mastery']}")

    print("\n" + "=" * 60)
    print("测试3: 检测知识空白")
    gaps = lm.get_knowledge_gaps("test_user")
    for gap in gaps:
        print(f"主题: {gap['topic']}")
        print(f"内容: {gap['content'][:50]}...")
        print(f"掌握度: {gap['mastery_level']:.0%}")
        print(f"空白分数: {gap['gap_score']:.2f}")
        print()

    lm.close()
    print("=" * 60)
    print("所有测试完成！")
