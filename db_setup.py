from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# 优先使用 DATABASE_URL，如果没有则构建PostgreSQL URL
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
    connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite')
    else {'client_encoding': 'utf8'}
)
Base = declarative_base()

# 创建Session工厂
# expire_on_commit=False: 提交后对象不过期,避免查询问题
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True)
    content = Column(Text)
    tag = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    # v0.6.0 Phase 3字段: 需要数据库迁移后启用
    # importance_score = Column(Float, default=0.0)  # 重要性分数(0-1)
    # access_count = Column(Integer, default=0)  # 访问次数
    # last_accessed_at = Column(DateTime, default=datetime.now)  # 最后访问时间
    # is_archived = Column(Boolean, default=False)  # 是否已归档


class Conversation(Base):
    """对话会话表"""
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, index=True)
    user_id = Column(String(50), default="default_user")
    title = Column(String(200))
    pinned = Column(Boolean, default=False)  # v0.8.1 置顶标记
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Message(Base):
    """对话消息表"""
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20))  # user / assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    image_path = Column(String(500))  # v0.8.1 图片路径


class UserBehavior(Base):
    """用户行为统计表 - v0.3.0 Learning层"""
    __tablename__ = "user_behaviors"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    # 对话统计
    message_count = Column(Integer, default=0)  # 本次会话消息数
    user_message_count = Column(Integer, default=0)  # 用户消息数
    avg_message_length = Column(Integer, default=0)  # 平均消息长度
    # 时间统计
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, default=datetime.now)
    duration_seconds = Column(Integer, default=0)  # 会话时长（秒）
    # 话题标签（从记忆中提取）
    topics = Column(Text)  # JSON格式存储话题列表
    # v0.8.2: 新增情感分析和交互类型
    sentiment_score = Column(Float, default=0.0)  # 情感分数 (-1.0 ~ 1.0)
    interaction_type = Column(String(50), default="chat")  # 交互类型: chat/task/qa
    # 记录时间
    created_at = Column(DateTime, default=datetime.now)


class ProactiveQuestion(Base):
    """主动问答记录表 - v0.3.0 Learning层"""
    __tablename__ = "proactive_questions"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    # 原始问题
    original_question = Column(Text)  # 用户原始提问
    question_type = Column(String(50))  # 问题类型：incomplete/clarification/summary
    # 问答状态
    is_answered = Column(Boolean, default=False)  # 是否已完整回答
    need_followup = Column(Boolean, default=True)  # 是否需要追问
    # 追问内容
    followup_question = Column(Text)  # AI生成的追问内容
    followup_asked = Column(Boolean, default=False)  # 是否已经追问
    # 分析结果
    missing_info = Column(Text)  # 缺失的信息点（JSON格式）
    confidence_score = Column(Integer, default=0)  # 判断置信度（0-100）
    # 时间记录
    created_at = Column(DateTime, default=datetime.now)
    asked_at = Column(DateTime)  # 追问时间
    answered_at = Column(DateTime)  # 回答时间


class LearnedPattern(Base):
    """学习模式表 - v0.3.0 Learning层"""
    __tablename__ = "learned_patterns"

    pattern_id = Column(Integer, primary_key=True)
    user_id = Column(String(50), default="default_user", index=True)

    # 模式类型：frequent_word(高频词), synonym(同义词),
    # common_question(常见问题), user_preference(用户偏好)
    pattern_type = Column(String(50), index=True)

    # 模式数据（JSON格式）
    # 高频词: {"word": "天气", "context": ["今天", "明天"]}
    # 同义词: {"word": "你好", "synonyms": ["您好", "hi"]}
    # 常见问题: {"question": "天气怎么样", "category": "天气查询"}
    # 用户偏好: {"preference": "喜欢简短回答", "strength": 0.8}
    pattern_data = Column(Text)

    # 统计数据
    frequency = Column(Integer, default=1)  # 出现频次
    confidence = Column(Integer, default=50)  # 置信度 0-100

    # 时间记录
    created_at = Column(DateTime, default=datetime.now)
    last_seen_at = Column(DateTime, default=datetime.now)  # 最后出现时间


class ToolExecution(Base):
    """工具执行记录表 - v0.4.0 Action层"""
    __tablename__ = "tool_executions"

    execution_id = Column(Integer, primary_key=True)
    tool_name = Column(String(100), index=True)  # 工具名称
    user_id = Column(String(50), default="default_user", index=True)
    session_id = Column(String(100), index=True)  # 会话ID

    # 执行参数和结果
    parameters = Column(Text)  # JSON格式的参数
    result = Column(Text)  # JSON格式的结果
    success = Column(Boolean, default=True)  # 是否成功
    error_message = Column(Text)  # 错误信息

    # 性能指标
    execution_time = Column(Float, default=0.0)  # 执行时间(秒)

    # 时间记录
    executed_at = Column(DateTime, default=datetime.now, index=True)


class FaceEncoding(Base):
    """人脸特征向量表 - v0.9.0 Phase 1"""
    __tablename__ = "face_encodings"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), default="default_user", index=True)
    name = Column(String(100), nullable=False)  # 人名

    # 128维特征向量 (PostgreSQL ARRAY)
    # 注意: SQLite不支持ARRAY，如果使用SQLite需改为JSON存储
    encoding = Column(ARRAY(Float))

    image_path = Column(String(500))  # 来源图片路径
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


Base.metadata.create_all(engine)
print("✅ 数据库初始化完成。")
