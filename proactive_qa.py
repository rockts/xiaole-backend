"""
主动问答模块 - v0.7.0 智能优化版
基于上下文、记忆和不确定性的智能提问系统

v0.7.0 重大更新:
- 集成记忆层，读取用户偏好和历史学习内容
- 基于"知识空白"和"不确定性"触发提问
- 检测信息冲突（新旧信息不一致）
- 任务反馈追踪（任务完成但未反馈）
- 上下文连贯性分析

v0.6.2更新:
- 添加问题去重机制，避免重复追问
- 添加冷却时间，避免频繁打扰
- 改进上下文敏感判断
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db_setup import ProactiveQuestion, Message
from datetime import datetime, timedelta
from backend.memory import MemoryManager
from backend.learning import get_learning_manager  # v0.7.0 学习层集成
import os
import re
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
    connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite')
    else {'client_encoding': 'utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ====================
# 智能触发器类 - v0.7.0新增
# ====================
class SmartTrigger:
    """
    基于上下文和不确定性的智能触发器

    触发场景：
    1. 知识空白：用户提问但AI回答模糊/不完整
    2. 信息冲突：新回答与历史记忆矛盾
    3. 任务反馈：任务完成但用户未反馈效果
    4. 学习延续：上次话题中断，可继续深入
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    def detect_knowledge_gap(self, question: str, answer: str) -> tuple[bool, str]:
        """
        检测知识空白
        返回: (是否有空白, 缺失信息类型)
        """
        # 1. 检测模糊回答标记词
        uncertainty_markers = [
            "可能", "大概", "应该", "或许", "不太确定",
            "我猜", "似乎", "好像", "也许"
        ]

        # 排除明确性词汇（避免误判）
        certainty_indicators = [
            "已经", "确认", "明确", "肯定", "一定", "必须",
            "完成", "删除", "更新", "修改", "保存"
        ]

        # 如果回答中包含明确性词汇，降低触发概率
        has_certainty = any(
            indicator in answer for indicator in certainty_indicators
        )
        has_uncertainty = any(
            marker in answer for marker in uncertainty_markers
        )

        # 只有在有不确定词且没有明确词时才触发
        if has_uncertainty and not has_certainty:
            return True, "模糊回答_需要明确"

        # 2. 检测回答过短（问题复杂但回答简单）
        if len(question) > 20 and len(answer) < 50:
            return True, "回答过简_需要展开"

        # 3. 检测缺少关键信息（如时间、地点、方式）
        question_lower = question.lower()
        if any(word in question_lower for word in ["什么时候", "when", "何时"]):
            if not any(word in answer for word in ["时间", "日期", "点", "月", "年"]):
                return True, "缺少时间信息"

        if any(word in question_lower for word in ["怎么", "如何", "how"]):
            if len(answer) < 100:  # 方法类问题回答应该详细
                return True, "缺少步骤说明"

        return False, ""

    def detect_memory_conflict(self, new_fact: str) -> tuple[bool, str]:
        """
        检测新信息与历史记忆的冲突
        返回: (是否冲突, 冲突的旧信息)

        v0.7.0优化: 使用更智能的相似度匹配
        """
        # 从记忆层获取相关历史facts（使用recall方法）
        memories = self.memory.recall(tag="facts", keyword=None, limit=10)

        for old_fact in memories:
            # 1. 简单冲突检测：检查否定词
            if self._has_negation_conflict(new_fact, old_fact):
                return True, old_fact

            # 2. 语义冲突检测：内容相似但含义相反
            if self._has_semantic_conflict(new_fact, old_fact):
                return True, old_fact

        return False, ""

    def _has_semantic_conflict(self, new: str, old: str) -> bool:
        """
        检测语义冲突（更智能的匹配）
        例如："喜欢咖啡" vs "讨厌咖啡"
        """
        # 提取主题词（名词）
        def extract_subject(text: str) -> str:
            """简单提取主题词"""
            # 移除常见动词和情感词
            remove_words = [
                "喜欢", "不喜欢", "爱", "讨厌", "想", "不想",
                "要", "不要", "会", "不会", "能", "不能",
                "是", "不是", "有", "没有"
            ]
            result = text
            for word in remove_words:
                result = result.replace(word, "")
            return result.strip()

        new_subject = extract_subject(new)
        old_subject = extract_subject(old)

        # 如果主题词相似度>70%，但含义相反
        if new_subject and old_subject:
            similarity = self._calculate_text_similarity(
                new_subject, old_subject)
            if similarity > 0.7:
                # 检查情感极性是否相反
                positive_words = ["喜欢", "爱", "想", "要", "会", "能", "是", "有"]
                negative_words = ["不喜欢", "讨厌", "不想", "不要", "不会",
                                  "不能", "不是", "没有", "无", "非"]

                new_is_positive = any(w in new for w in positive_words)
                new_is_negative = any(w in new for w in negative_words)
                old_is_positive = any(w in old for w in positive_words)
                old_is_negative = any(w in old for w in negative_words)

                # 一个积极一个消极 → 冲突
                if (new_is_positive and old_is_negative) or \
                   (new_is_negative and old_is_positive):
                    return True

        return False

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（0-1）"""
        if not text1 or not text2:
            return 0.0

        # 字符级Jaccard相似度
        chars1 = set(text1)
        chars2 = set(text2)

        intersection = len(chars1 & chars2)
        union = len(chars1 | chars2)

        return intersection / union if union > 0 else 0.0

    def _has_negation_conflict(self, new: str, old: str) -> bool:
        """检测否定冲突（如"喜欢咖啡" vs "不喜欢咖啡"）"""
        negation_words = ["不", "没", "无", "非", "never", "no", "not"]

        # 提取关键词（去除否定词）
        new_clean = new
        old_clean = old
        for neg in negation_words:
            new_clean = new_clean.replace(neg, "")
            old_clean = old_clean.replace(neg, "")

        # 如果去除否定词后相似，但原文中一个有否定词一个没有→冲突
        if new_clean == old_clean:
            new_has_neg = any(neg in new for neg in negation_words)
            old_has_neg = any(neg in old for neg in negation_words)
            if new_has_neg != old_has_neg:
                return True

        return False

    def detect_task_feedback_missing(self, session_id: str) -> tuple[bool, str]:
        """
        检测任务完成但缺少反馈
        返回: (是否需要反馈, 任务描述)

        场景：AI执行了文件操作/提醒设置，但用户没有确认效果
        """
        session = SessionLocal()
        try:
            # 获取最近5条消息
            recent = session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at.desc()).limit(5).all()

            if not recent:
                return False, ""

            # 检测任务执行标志
            task_keywords = ["已设置", "已保存", "已创建", "完成", "done", "created"]
            feedback_keywords = ["谢谢", "好的", "收到", "明白了", "不错", "很好"]

            for msg in recent[:3]:  # 只检查最近3条
                if msg.role == "assistant":
                    content = msg.content.lower()
                    # AI提到完成任务
                    if any(kw in content for kw in task_keywords):
                        # 检查后续是否有用户反馈
                        has_feedback = False
                        for next_msg in recent:
                            if (next_msg.created_at > msg.created_at and
                                    next_msg.role == "user"):
                                if any(kw in next_msg.content
                                       for kw in feedback_keywords):
                                    has_feedback = True
                                    break

                        if not has_feedback:
                            # 提取任务描述
                            task_desc = self._extract_task_description(
                                msg.content
                            )
                            return True, task_desc

            return False, ""
        finally:
            session.close()

    def _extract_task_description(self, text: str) -> str:
        """从AI回复中提取任务描述"""
        # 简单提取：找"已"字前的动词短语
        patterns = [
            r"([\u4e00-\u9fa5]{2,6})已",  # "设置提醒已"
            r"已([\u4e00-\u9fa5]{2,6})",  # "已创建文件"
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "任务"

    def detect_user_impatience(self, session_id: str) -> tuple[bool, str]:
        """
        检测用户不耐烦情绪
        返回: (是否不耐烦, 原因)

        v0.7.0新增: 情感感知，避免过度追问
        """
        session = SessionLocal()
        try:
            # 获取最近3条用户消息
            recent_user_msgs = session.query(Message).filter(
                Message.session_id == session_id,
                Message.role == "user"
            ).order_by(Message.created_at.desc()).limit(3).all()

            if len(recent_user_msgs) < 2:
                return False, ""

            # 不耐烦标志词
            impatience_markers = [
                "别问了", "不要问", "够了", "算了", "随便", "无所谓",
                "不想说", "不用", "不需要", "停", "别", "烦",
                "知道了", "明白了", "懂了", "行了", "好了"
            ]

            # 检查最近的消息
            latest_msg = recent_user_msgs[0].content
            for marker in impatience_markers:
                if marker in latest_msg:
                    return True, f"用户表达不耐烦: '{marker}'"

            # 检测重复短回复（如连续的"嗯"、"好"）
            if len(recent_user_msgs) >= 2:
                msg1 = recent_user_msgs[0].content.strip()
                msg2 = recent_user_msgs[1].content.strip()

                if len(msg1) <= 2 and len(msg2) <= 2:
                    if msg1 == msg2 or msg1 in ["嗯", "哦", "好", "行"]:
                        return True, "用户连续短回复，可能失去兴趣"

            return False, ""
        finally:
            session.close()


class ProactiveQA:
    """主动问答分析器"""

    # v0.6.0: 可配置的置信度阈值
    CONFIDENCE_THRESHOLD = int(os.getenv('PROACTIVE_QA_THRESHOLD', '65'))

    # 问题关键词模式
    QUESTION_PATTERNS = [
        r'(什么|啥|什么时候|哪里|哪个|哪种|哪|谁|多少|几个|怎么|为什么|如何|怎样)',  # 疑问词
        r'(吗|呢|啊)\s*\??$',  # 句尾语气词
        r'\?',  # 问号
    ]

    # 不完整回答标记
    INCOMPLETE_MARKERS = [
        '不知道', '不清楚', '不太确定', '不记得', '忘了',
        '说不上来', '不好说', '看情况', '再说', '以后',
        '可能', '大概', '应该', '或许', '也许',
    ]

    def __init__(self, confidence_threshold=None):
        """
        初始化

        Args:
            confidence_threshold: 自定义置信度阈值（默认使用环境变量）
        """
        self.confidence_threshold = (
            confidence_threshold or self.CONFIDENCE_THRESHOLD
        )
        # v0.6.2: 问题去重配置
        self.recent_questions = []  # 最近追问的问题
        self.max_recent = 10  # 保留最近10个问题用于去重
        self.cooldown_seconds = 300  # 同一问题冷却时间（5分钟）
        self.last_ask_time = None  # 上次追问时间

        # v0.7.0: 集成记忆管理器和智能触发器
        self.memory = MemoryManager()
        self.smart_trigger = SmartTrigger(self.memory)

    def is_question(self, text: str) -> bool:
        """判断文本是否为问句"""
        if not text:
            return False

        # 检查问题模式
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _is_duplicate_question(self, question: str) -> bool:
        """
        检查是否为重复问题（v0.6.2）

        Args:
            question: 问题文本

        Returns:
            bool: 如果是重复问题且在冷却期内返回True
        """
        current_time = datetime.now()

        # 清理过期的问题记录
        self.recent_questions = [
            (q, t) for q, t in self.recent_questions
            if (current_time - t).total_seconds() < self.cooldown_seconds
        ]

        # 检查是否为相似问题（简单的相似度判断）
        for recent_q, ask_time in self.recent_questions:
            # 计算文本相似度（简单版：检查关键词重叠）
            if self._calculate_similarity(question, recent_q) > 0.7:
                return True

        return False

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（简单版本）

        Returns:
            float: 0-1之间的相似度分数
        """
        # 分词（简单版：按字符）
        words1 = set(text1)
        words2 = set(text2)

        if not words1 or not words2:
            return 0.0

        # 计算Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _add_to_recent_questions(self, question: str):
        """
        添加问题到最近问题列表（v0.6.2）

        Args:
            question: 问题文本
        """
        self.recent_questions.append((question, datetime.now()))

        # 限制列表大小
        if len(self.recent_questions) > self.max_recent:
            self.recent_questions.pop(0)

        # 更新上次追问时间
        self.last_ask_time = datetime.now()

    def _should_cooldown(self) -> bool:
        """
        检查是否应该冷却（避免频繁追问）

        Returns:
            bool: 如果应该冷却返回True
        """
        if not self.last_ask_time:
            return False

        # 至少间隔30秒再追问
        time_since_last = (datetime.now() - self.last_ask_time).total_seconds()
        return time_since_last < 30

    def is_incomplete_answer(self, text: str) -> bool:
        """
        判断回答是否不完整

        v0.6.0优化:
        - 排除明显完整的回答
        - 减少误判率
        """
        if not text:
            return True

        # 排除明显完整的回答（包含详细解释词汇）
        complete_indicators = [
            '具体来说', '详细地说', '总而言之', '综上所述',
            '因此', '所以说', '总之', '例如', '比如说',
            '第一', '第二', '首先', '其次', '最后',
            '步骤', '方法如下', '可以这样', '建议'
        ]

        # 如果包含完整性指示词且长度>20，认为是完整回答
        if len(text) > 20:
            if any(indicator in text for indicator in complete_indicators):
                return False

        # 检查不完整标记
        for marker in self.INCOMPLETE_MARKERS:
            if marker in text:
                return True

        # 回答过短（少于5个字）
        if len(text.strip()) < 5:
            return True

        return False

    def analyze_conversation(
        self, session_id: str, user_id: str = "default_user"
    ) -> dict:
        """
        分析对话，识别需要追问的问题

        返回格式：
        {
            "needs_followup": bool,
            "questions": [
                {
                    "question": str,
                    "type": str,
                    "missing_info": list,
                    "confidence": int
                }
            ]
        }
        """
        session = SessionLocal()
        try:
            # 获取该会话的最近20条消息
            messages = (
                session.query(Message)
                .filter_by(session_id=session_id)
                .order_by(Message.created_at.desc())
                .limit(20)
                .all()
            )

            if not messages:
                return {"needs_followup": False, "questions": []}

            # v0.6.2: 检查是否应该冷却
            if self._should_cooldown():
                return {"needs_followup": False, "questions": []}

            # v0.7.0: 情感感知 - 检测用户是否不耐烦
            is_impatient, reason = self.smart_trigger.detect_user_impatience(
                session_id
            )
            if is_impatient:
                print(f"😔 检测到用户不耐烦: {reason}，停止追问")
                return {"needs_followup": False, "questions": []}

            # 反转消息顺序（从旧到新）
            messages = list(reversed(messages))

            needs_followup_list = []

            # 分析消息对
            for i in range(len(messages) - 1):
                current_msg = messages[i]
                next_msg = messages[i + 1]

                # 查找：用户提问 -> AI回答的模式
                if (current_msg.role == "user" and
                        next_msg.role == "assistant"):

                    user_text = current_msg.content
                    ai_response = next_msg.content

                    # 判断用户是否提问
                    if self.is_question(user_text):
                        # v0.6.2: 检查是否为重复问题
                        if self._is_duplicate_question(user_text):
                            continue

                        # 判断AI回答是否不完整
                        if self.is_incomplete_answer(ai_response):
                            # 分析缺失信息
                            missing_info = self._analyze_missing_info(
                                user_text, ai_response
                            )

                            # 计算置信度
                            confidence = self._calculate_confidence(
                                user_text, ai_response, missing_info
                            )

                            # v0.6.2: 记录问题用于去重
                            self._add_to_recent_questions(user_text)

                            needs_followup_list.append({
                                "question": user_text,
                                "type": "incomplete",
                                "missing_info": missing_info,
                                "confidence": confidence,
                                "ai_response": ai_response
                            })

            # v0.7.0: 智能触发 - 检测知识空白、信息冲突、任务反馈
            for i in range(len(messages) - 1):
                current_msg = messages[i]
                next_msg = messages[i + 1]

                if (current_msg.role == "user" and
                        next_msg.role == "assistant"):

                    user_text = current_msg.content
                    ai_response = next_msg.content

                    # 1. 知识空白检测
                    has_gap, gap_type = (
                        self.smart_trigger.detect_knowledge_gap(
                            user_text, ai_response
                        )
                    )
                    if has_gap:
                        needs_followup_list.append({
                            "question": user_text,
                            "type": "knowledge_gap",
                            "missing_info": [gap_type],
                            "confidence": 75,
                            "ai_response": ai_response,
                            "reason": f"检测到{gap_type}"
                        })

                    # 2. 信息冲突检测（从AI回复中提取可能的fact）
                    if len(ai_response) > 30:  # 只分析较长的回复
                        has_conflict, old_fact = (
                            self.smart_trigger.detect_memory_conflict(
                                ai_response[:200]  # 取前200字符
                            )
                        )
                        if has_conflict:
                            needs_followup_list.append({
                                "question": user_text,
                                "type": "memory_conflict",
                                "missing_info": ["信息冲突"],
                                "confidence": 80,
                                "ai_response": ai_response,
                                "reason": f"与历史记忆冲突: {old_fact}"
                            })

            # 3. 任务反馈检测（检查整个会话）
            needs_feedback, task_desc = (
                self.smart_trigger.detect_task_feedback_missing(session_id)
            )
            if needs_feedback:
                needs_followup_list.append({
                    "question": f"{task_desc}完成情况反馈",
                    "type": "task_feedback",
                    "missing_info": ["用户反馈"],
                    "confidence": 70,
                    "ai_response": "",
                    "reason": f"任务'{task_desc}'已完成，但用户未反馈效果"
                })

            # 检查是否有需要追问的问题
            needs_followup = len(needs_followup_list) > 0

            return {
                "needs_followup": needs_followup,
                "questions": needs_followup_list
            }

        finally:
            session.close()

    def _analyze_missing_info(
        self, question: str, answer: str
    ) -> list:
        """分析缺失的信息点"""
        missing = []

        # 提取问题中的关键信息点
        if '什么' in question or '啥' in question:
            if not any(word in answer for word in ['是', '叫', '指']):
                missing.append("具体名称")

        if '怎么' in question or '如何' in question:
            if not any(word in answer for word in ['步骤', '方法', '可以']):
                missing.append("操作方法")

        if '为什么' in question:
            if not any(word in answer for word in ['因为', '由于', '原因']):
                missing.append("原因说明")

        if '多少' in question or '几' in question:
            if not any(char.isdigit() for char in answer):
                missing.append("具体数值")

        if '哪' in question or '谁' in question:
            missing.append("具体对象")

        # 如果没有识别到具体缺失点，给出通用描述
        if not missing:
            missing.append("完整回答")

        return missing

    def _calculate_confidence(
        self, question: str, answer: str, missing_info: list
    ) -> int:
        """
        计算判断置信度（0-100）

        v0.6.0优化:
        - 调整基础分为40（降低误判）
        - 优化不完整标记权重
        - 考虑回答长度更细致
        - 添加问题复杂度因素
        """
        confidence = 40  # 基础分（从50降低到40，减少误触发）

        # 1. 根据不完整标记增加置信度
        incomplete_count = sum(
            1 for marker in self.INCOMPLETE_MARKERS if marker in answer
        )
        if incomplete_count >= 2:
            confidence += 25  # 多个标记词，强烈暗示不完整
        elif incomplete_count == 1:
            confidence += 15  # 单个标记词

        # 2. 回答长度分析（更细致的评分）
        answer_length = len(answer.strip())
        if answer_length < 5:
            confidence += 35  # 极短回答
        elif answer_length < 10:
            confidence += 25  # 很短回答
        elif answer_length < 20:
            confidence += 15  # 较短回答
        elif answer_length < 30:
            confidence += 5   # 中等长度，可能不完整

        # 3. 缺失信息评分
        confidence += len(missing_info) * 5

        # 4. 问题复杂度（复杂问题更需要详细回答）
        question_length = len(question)
        if question_length > 30 and answer_length < question_length * 0.5:
            confidence += 10  # 问题长但回答短

        # 5. 特殊情况调整
        # 如果回答中有举例、解释等词，降低置信度
        if any(word in answer for word in ['例如', '比如', '就是', '也就是说', '具体来说']):
            confidence -= 10

        # 如果回答中有明确的结论性词汇，降低置信度
        if any(word in answer for word in ['总之', '综上', '因此', '所以说']):
            confidence -= 15

        # 限制在0-100范围
        return min(max(confidence, 0), 100)

    def generate_followup_question(
        self, original_question: str, missing_info: list, ai_response: str,
        question_type: str = "incomplete", reason: str = ""
    ) -> str:
        """
        生成追问内容

        v0.7.0优化:
        - 支持多种触发类型（知识空白、信息冲突、任务反馈）
        - 更智能的上下文感知追问

        v0.6.0优化:
        - 更自然的表达方式
        - 根据回答内容调整追问策略
        - 添加多样化的追问模板
        """
        import random

        # v0.7.0: 新类型追问
        if question_type == "knowledge_gap":
            if "模糊回答" in reason:
                return "刚才的回答中我看到有些不确定的地方，能再确认一下吗？"
            elif "回答过简" in reason:
                return "这个问题可以再详细说说吗？"
            elif "缺少时间" in reason:
                return "具体是什么时候呢？"
            elif "缺少步骤" in reason:
                return "能说说具体怎么操作吗？"

        if question_type == "memory_conflict":
            old_info = reason.split(":")[-1].strip() if ":" in reason else ""
            if old_info:
                return f"我记得之前你说过「{old_info}」，这次的说法好像不太一样？"
            else:
                return "这个信息和之前的记忆有点不一样，能确认一下吗？"

        if question_type == "task_feedback":
            task = original_question.replace("完成情况反馈", "").strip()
            templates = [
                f"刚才的{task}完成了，效果怎么样？",
                f"{task}已经设置好了，还有什么需要调整的吗？",
                f"关于{task}，有什么问题或建议吗？"
            ]
            return random.choice(templates)

        # 原有逻辑：不完整回答追问
        # 截取问题（太长则省略）
        question_preview = original_question
        if len(original_question) > 40:
            question_preview = original_question[:40] + "..."

        # 根据缺失信息类型生成追问
        if "具体名称" in missing_info:
            templates = [
                f"关于「{question_preview}」，您能说得更具体一些吗？",
                f"「{question_preview}」这个问题，能详细解释一下吗？",
                f"刚才提到的「{question_preview}」，具体是指什么呢？"
            ]
            return random.choice(templates)

        if "操作方法" in missing_info:
            templates = [
                f"关于「{question_preview}」，能详细说说具体步骤吗？",
                f"「{question_preview}」这个操作，具体该怎么做呢？",
                f"您能展开讲讲「{question_preview}」的具体方法吗？"
            ]
            return random.choice(templates)

        if "原因说明" in missing_info:
            templates = [
                f"关于「{question_preview}」，能再说说具体原因吗？",
                f"为什么会这样呢？能详细解释下「{question_preview}」吗？",
                f"「{question_preview}」背后的原因是什么呢？"
            ]
            return random.choice(templates)

        if "具体数值" in missing_info:
            templates = [
                f"「{question_preview}」，大概是多少呢？",
                f"关于「{question_preview}」，能给个具体的数字吗？",
                f"能具体说说「{question_preview}」的数量吗？"
            ]
            return random.choice(templates)

        if "具体对象" in missing_info:
            templates = [
                f"「{question_preview}」，具体是指哪个呢？",
                f"关于「{question_preview}」，您说的是哪一个？",
                f"能明确一下「{question_preview}」说的是谁/什么吗？"
            ]
            return random.choice(templates)

        # 通用追问（根据回答长度选择）
        if len(ai_response) < 10:
            templates = [
                f"「{question_preview}」这个问题，能展开说说吗？",
                f"关于「{question_preview}」，能再详细一点吗？",
                f"「{question_preview}」能具体解释一下吗？"
            ]
        else:
            templates = [
                f"「{question_preview}」这个话题，还能再多说一点吗？",
                f"关于「{question_preview}」，我想了解更多细节",
                f"「{question_preview}」能补充说明一下吗？"
            ]

        return random.choice(templates)

    def save_proactive_question(
        self,
        session_id: str,
        user_id: str,
        original_question: str,
        question_type: str,
        missing_info: list,
        confidence: int,
        followup_question: str
    ) -> int:
        """保存主动问答记录，返回记录ID（自动去重）"""
        session = SessionLocal()
        try:
            # 检查是否已存在相同的未回答问题（基于user_id去重，避免跨会话重复）
            # 只检查最近10分钟内的记录，避免误删旧记录
            ten_minutes_ago = datetime.now() - timedelta(minutes=10)

            existing = (
                session.query(ProactiveQuestion)
                .filter_by(
                    user_id=user_id,
                    original_question=original_question,
                    followup_asked=False
                )
                .filter(ProactiveQuestion.created_at >= ten_minutes_ago)
                .first()
            )

            if existing:
                # 如果已存在，更新置信度（取较高值）并返回现有记录ID
                if confidence > existing.confidence_score:
                    existing.confidence_score = confidence
                    session.commit()
                return existing.id

            # 不存在则创建新记录
            record = ProactiveQuestion(
                user_id=user_id,
                session_id=session_id,
                original_question=original_question,
                question_type=question_type,
                is_answered=False,
                need_followup=True,
                followup_question=followup_question,
                followup_asked=False,
                missing_info=json.dumps(missing_info, ensure_ascii=False),
                confidence_score=confidence
            )
            session.add(record)
            session.commit()
            return record.id
        finally:
            session.close()

    def get_pending_followups(
        self, session_id: str, limit: int = 5
    ) -> list:
        """获取待追问的问题列表（按user_id去重，避免跨会话重复）"""
        session = SessionLocal()
        try:
            # 先获取该会话的user_id
            from backend.db_setup import Message
            msg = session.query(Message).filter_by(
                session_id=session_id).first()
            user_id = msg.user_id if msg else "default_user"

            # 查询该用户的待追问问题（不限定session_id，避免跨会话重复显示）
            # 使用子查询去重：每个original_question只保留最新的一条
            from sqlalchemy import func
            subquery = (
                session.query(
                    ProactiveQuestion.original_question,
                    func.max(ProactiveQuestion.id).label('max_id')
                )
                .filter_by(user_id=user_id, followup_asked=False)
                .group_by(ProactiveQuestion.original_question)
                .subquery()
            )

            records = (
                session.query(ProactiveQuestion)
                .join(
                    subquery,
                    ProactiveQuestion.id == subquery.c.max_id
                )
                .order_by(ProactiveQuestion.confidence_score.desc())
                .limit(limit)
                .all()
            )

            result = []
            for record in records:
                result.append({
                    "id": record.id,
                    "question": record.original_question,
                    "followup": record.followup_question,
                    "confidence": record.confidence_score,
                    "created_at": record.created_at.isoformat()
                })
            return result
        finally:
            session.close()

    def mark_followup_asked(self, question_id: int):
        """标记追问已发送"""
        session = SessionLocal()
        try:
            record = session.query(ProactiveQuestion).get(question_id)
            if record:
                record.followup_asked = True
                record.asked_at = datetime.now()
                session.commit()
        finally:
            session.close()

    def get_followup_history(
        self, session_id: str = None, user_id: str = None, limit: int = 20
    ) -> list:
        """获取追问历史记录（去重显示，每个问题只显示最新一条）"""
        session = SessionLocal()
        try:
            # 如果没有指定user_id，尝试从session_id获取
            if not user_id and session_id:
                from backend.db_setup import Message
                msg = session.query(Message).filter_by(
                    session_id=session_id
                ).first()
                if msg:
                    user_id = msg.user_id

            # 使用user_id查询，避免session_id限制导致的重复
            if user_id:
                # 子查询：每个问题保留最新的一条记录
                from sqlalchemy import func
                subquery = (
                    session.query(
                        ProactiveQuestion.original_question,
                        func.max(ProactiveQuestion.id).label('max_id')
                    )
                    .filter_by(user_id=user_id)
                    .group_by(ProactiveQuestion.original_question)
                    .subquery()
                )

                records = (
                    session.query(ProactiveQuestion)
                    .join(
                        subquery,
                        ProactiveQuestion.id == subquery.c.max_id
                    )
                    .order_by(ProactiveQuestion.created_at.desc())
                    .limit(limit)
                    .all()
                )
            else:
                # 没有user_id，使用原逻辑（不去重）
                query = session.query(ProactiveQuestion)
                if session_id:
                    query = query.filter_by(session_id=session_id)
                records = (
                    query.order_by(ProactiveQuestion.created_at.desc())
                    .limit(limit)
                    .all()
                )

            result = []
            for record in records:
                result.append({
                    "id": record.id,
                    "original_question": record.original_question,
                    "followup_question": record.followup_question,
                    "type": record.question_type,
                    "confidence": record.confidence_score,
                    "followup_asked": record.followup_asked,
                    "created_at": record.created_at.isoformat(),
                    "asked_at": (
                        record.asked_at.isoformat()
                        if record.asked_at else None
                    )
                })
            return result
        finally:
            session.close()
