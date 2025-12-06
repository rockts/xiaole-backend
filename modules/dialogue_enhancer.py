"""
v0.6.0 Phase 3 Day 4: 对话质量提升

- 情感识别和回应
- 风格一致性控制
- 多轮上下文优化
"""

import re
from typing import Dict, List, Any, Optional


class DialogueEnhancer:
    """对话质量增强器"""

    def __init__(self):
        # 情感关键词映射
        self.emotion_keywords = {
            'joy': ['开心', '高兴', '快乐', '哈哈', '😊', '😄', '棒', '太好了'],
            'sadness': ['难过', '伤心', '失望', '沮丧', '😢', '😭', '唉'],
            'anger': ['生气', '愤怒', '烦', '讨厌', '😠', '😡', '气死了'],
            'fear': ['害怕', '担心', '紧张', '焦虑', '😰', '😨'],
            'surprise': ['惊讶', '意外', '没想到', '😲', '😮', '竟然'],
            'neutral': ['嗯', '好的', '知道了', '明白']
        }

        # 情感回应模板
        self.emotion_responses = {
            'joy': ['太好了！', '真为你高兴！', '这真是个好消息！'],
            'sadness': ['我理解你的感受', '别太难过', '会好起来的'],
            'anger': ['我明白你的感受', '深呼吸，冷静一下', '有什么我能帮到你的吗？'],
            'fear': ['别担心', '一切都会好的', '我会陪着你'],
            'surprise': ['是的，确实挺意外的', '没想到吧', '挺有意思的']
        }

    def detect_emotion(self, text: str) -> str:
        """检测文本情感"""
        text_lower = text.lower()
        emotion_scores = {}

        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                emotion_scores[emotion] = score

        if not emotion_scores:
            return 'neutral'

        return max(emotion_scores.items(), key=lambda x: x[1])[0]

    def add_empathy_prefix(self, emotion: str, response: str) -> str:
        """添加共情前缀"""
        if emotion == 'neutral' or not emotion:
            return response

        if emotion in self.emotion_responses:
            import random
            prefix = random.choice(self.emotion_responses[emotion])
            return f"{prefix} {response}"

        return response

    def optimize_context_window(
        self,
        history: List[Dict],
        max_messages: int = 10
    ) -> List[Dict]:
        """优化上下文窗口"""
        if len(history) <= max_messages:
            return history

        # 保留最近的消息
        recent = history[-max_messages:]

        # 提取重要信息（包含关键词的消息）
        important_keywords = ['记住', '提醒', '重要', '一定', '务必']
        important_msgs = [
            msg for msg in history[:-max_messages]
            if any(kw in msg.get('content', '') for kw in important_keywords)
        ]

        # 合并：重要消息 + 最近消息
        return important_msgs[-3:] + recent if important_msgs else recent

    def ensure_style_consistency(
        self,
        response: str,
        style: str = 'balanced'
    ) -> str:
        """确保风格一致性"""
        if style == 'concise':
            # 简洁风格：去除多余修饰
            response = re.sub(r'其实|实际上|基本上|大概|可能', '', response)
            response = re.sub(r'([。！？])[，、]', r'\1', response)

        elif style == 'detailed':
            # 详细风格：保持原样或略微扩展
            pass

        elif style == 'professional':
            # 专业风格：使用正式用语
            replacements = {
                '我觉得': '我认为',
                '挺好': '很好',
                '有点': '略微',
                '太棒了': '非常出色'
            }
            for old, new in replacements.items():
                response = response.replace(old, new)

        return response.strip()

    def add_contextual_continuity(
        self,
        current_response: str,
        last_message: Optional[Dict] = None
    ) -> str:
        """添加上下文连续性"""
        if not last_message:
            return current_response

        last_content = last_message.get('content', '')

        # 如果上一条是问题，且当前回复很短，添加承接词
        if '？' in last_content or '吗' in last_content:
            if len(current_response) < 20:
                continuity_words = ['关于这个问题，', '针对你的疑问，', '']
                import random
                prefix = random.choice(continuity_words)
                if prefix:
                    current_response = prefix + current_response

        return current_response

    def enhance_response(
        self,
        response: str,
        user_input: str,
        history: List[Dict],
        style: str = 'balanced'
    ) -> str:
        """综合增强回复质量"""
        # 1. 检测情感
        emotion = self.detect_emotion(user_input)

        # 2. 添加共情
        response = self.add_empathy_prefix(emotion, response)

        # 3. 确保风格一致
        response = self.ensure_style_consistency(response, style)

        # 4. 添加上下文连续性
        last_msg = history[-1] if history else None
        response = self.add_contextual_continuity(response, last_msg)

        return response


class ConversationSummarizer:
    """对话摘要生成器"""

    @staticmethod
    def summarize_long_context(
        history: List[Dict],
        max_length: int = 200
    ) -> str:
        """总结长对话"""
        if len(history) <= 3:
            return ""

        # 提取关键点
        key_points = []
        for msg in history[:-3]:  # 不包括最近3条
            content = msg.get('content', '')
            if any(kw in content for kw in ['记住', '提醒', '重要']):
                # 截取前50字作为关键点
                key_points.append(content[:50])

        if not key_points:
            return ""

        summary = "之前我们讨论了：" + "；".join(key_points[:3])
        return summary[:max_length] + "..." if len(summary) > max_length else summary
