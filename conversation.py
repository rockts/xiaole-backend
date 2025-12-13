    # 工具函数：去除不可见字符（如 ASCII 控制字符、零宽空格等）
        import re
        # 匹配所有 C0/C1 控制字符和常见零宽字符
        invisible_pattern = r"[\x00-\x1F\x7F\u200B\u200C\u200D\uFEFF]"
        return re.sub(invisible_pattern, "", text)
"""
对话上下文管理模块
管理多轮对话会话和消息历史
"""
from db_setup import Conversation, Message, SessionLocal
from datetime import datetime
import os
import re
import uuid
from logger import logger

# 使用db_setup中统一的Session工厂
Session = SessionLocal


class ConversationManager:
    """对话管理器"""

    def __init__(self):
        pass

    def _strip_trailing_ellipsis(self, title: str) -> str:
        """展示前移除末尾的...或…，保持历史数据更整洁"""
        if not title:
            return title
        cleaned = title.rstrip()
        if cleaned.endswith('...'):
            cleaned = cleaned[:-3].rstrip()
        if cleaned.endswith('…'):
            cleaned = cleaned[:-1].rstrip()
        return cleaned or title

    def _derive_title(self, prompt):
        """根据首条用户内容生成简短标题"""
        default_title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # 可通过环境变量关闭自动标题，回退到时间戳
        if os.getenv("AUTO_TITLE", "1") in ["0", "false", "False"]:
            return default_title

        if not prompt:
            return default_title

        cleaned = re.sub(r"\s+", " ", str(prompt)).strip()
        # 轻量级公式/希腊字母修复，避免标题出现碎片化 LaTeX

        def _sanitize_math(s: str) -> str:
            if not s:
                return s
            # 常见 DeepSeek/Qwen 片段合并错误修复
            repl = (
                s.replace("$$", "$")
                .replace("\\alp$h$a$", "α")
                .replace("\\bet$a$", "β")
                .replace("\\gam$ma$", "γ")
            )
            # 常见 LaTeX 到 Unicode 的直接替换
            repl = repl.replace("\\alpha", "α").replace("αlpha", "α")
            repl = repl.replace("\\beta", "β").replace("βeta", "β")
            repl = repl.replace("\\gamma", "γ")
            # 清理形如 $a$ 的冗余美元符号
            repl = re.sub(r"\$(.*?)\$", r"\1", repl)
            # 去掉残留的散落美元符号
            repl = repl.replace("$", "")
            return repl

        cleaned = _sanitize_math(cleaned)
        if not cleaned:
            return default_title

        # 取第一句话/子句作为标题骨架
        parts = re.split(r"[。！？?!\.]+", cleaned, maxsplit=1)
        candidate = parts[0].strip() if parts else cleaned

        # 限长，直接截断
        max_len = 20
        if len(candidate) > max_len:
            candidate = candidate[:max_len]

        return candidate or default_title

    def _generate_better_title(self, prompt: str, reply: str) -> str:
        """根据首条用户消息 + 助手首个回复生成更贴近 ChatGPT 风格的简短标题

        规则：
        - 优先使用用户动词短语（如“解释…”，“查询…”，“设置提醒…”）作为开头
        - 结合关键名词提炼主题（设备/品牌/功能/地点等）
        - 长度控制在 12–24 字，必要时添加省略号
        - 兜底：使用助手回复的第一句片段
        """
        default_title = f"对话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        text_user = (prompt or '').strip()
        text_assist = (reply or '').strip()

        # 轻量级公式/希腊字母修复，避免标题出现碎片化 LaTeX
        def _sanitize_math(s: str) -> str:
            if not s:
                return s
            repl = (
                s.replace("$$", "$")
                .replace("\\alp$h$a$", "α")
                .replace("\\bet$a$", "β")
                .replace("\\gam$ma$", "γ")
            )
            repl = repl.replace("\\alpha", "α").replace("αlpha", "α")
            repl = repl.replace("\\beta", "β").replace("βeta", "β")
            repl = repl.replace("\\gamma", "γ")
            repl = re.sub(r"\$(.*?)\$", r"\1", repl)
            # 去掉残留的散落美元符号
            repl = repl.replace("$", "")
            return repl

        text_user = _sanitize_math(text_user)
        text_assist = _sanitize_math(text_assist)

        if not text_user and not text_assist:
            return default_title

        verbs = [
            '解释', '查询', '设置', '制作', '归档', '分析', '总结',
            '对比', '说明', '排查', '定位', '修复', '翻译', '介绍',
            '扫描', '识别', '整理', '规划', '安排', '统计', '优化',
            '设计', '生成', '配置', '调试', '部署', '安装', '升级',
            '测试', '监控', '校验', '核对', '比对', '评估', '演练',
            '复盘', '记录', '整理', '总结', '调研', '迁移', '发布'
        ]

        # 领域与主题关键词（优先提取）
        domain_keywords = [
            'OCR', 'OpenSSH', 'SSH', 'allowlist', 'Domain', 'API', 'API Key', 'Webhook',
            '端口', '权限', '麦克风权限', '相机权限', 'CORS', 'SSL', 'TLS', '证书',
            '透明方形 logo', 'logo', '图标', '视觉稿', 'Gemini', 'Gemini 3', 'Gemini 3 Pro',
            'DeepSeek', 'ChatGPT', 'OpenAI', 'iPhone', 'iPhone 16', 'iPhone 17', 'MacBook',
            '课程表', '提醒', '任务', '待办', '翻译', '归档', '对比', '总结', '统计', '公式', '符号',
            'α', 'β', 'γ', 'θ', 'Docker', 'Nginx', 'PostgreSQL', 'Redis', '数据库', '部署', '日志'
        ]

        # 品牌/型号模式
        brand_patterns = [
            r"(?:iPhone\s*\d+)",
            r"(?:Gemini\s*\d+)",
            r"(?:OpenSSH)",
        ]

        # 助手常见套话黑名单，避免直接变成标题
        assist_blacklist = [
            "根据我刚才搜索到的信息",
            "根据我刚才查询到的信息",
            "根据最新的搜索结果",
            "根据你的描述",
            "根据提供的信息",
            "抱歉",
            "很抱歉",
            "我无法",
            "这是一个",
            "这是我对",
            "以下是",
            "以下内容",
            "以下是我整理的",
            "以下为",
            "以下建议",
        ]

        # 选取用户句子的前子句
        def pick_clause(s: str) -> str:
            parts = re.split(r"[。！？?!\.，,]+", s)
            return parts[0].strip() if parts and parts[0].strip() else s.strip()

        clause = pick_clause(text_user)
        # 找到开头动词
        verb = next((v for v in verbs if clause.startswith(v)), None)

        # 提取名词/关键词（粗略）：保留字母数字汉字，去掉多余助词
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", clause)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # 主题提取：先看品牌/型号，再看关键词白名单
        topic = None
        for pat in brand_patterns:
            m = re.search(pat, clause, flags=re.IGNORECASE)
            if m:
                topic = m.group(0)
                break
        if not topic:
            for kw in domain_keywords:
                if kw in clause or kw in text_assist:
                    topic = kw
                    break

        candidate = cleaned
        if verb:
            # 动词 + 主题 组合
            if topic:
                complements = {
                    '解释': ["含义", "原理"],
                    '查询': ["价格", "方案"],
                    '设置': ["权限", "参数"],
                    '排查': ["错误", "故障"],
                    '定位': ["问题", "原因"],
                    '修复': ["故障", "问题"],
                    '分析': ["发布", "差异"],
                    '制作': ["方案", "图标"],
                    '生成': ["方案", "文案"],
                    '设计': ["方案", "版式"],
                    '配置': ["参数", "策略"],
                    '调试': ["流程", "接口"],
                    '部署': ["方案", "脚本"],
                    '测试': ["方案", "用例"],
                    '监控': ["指标", "报警"],
                    '归档': ["对话", "文档"],
                    '翻译': ["内容"],
                    '说明': ["流程"],
                    '优化': ["策略", "性能"],
                    '评估': ["风险", "影响"],
                    '总结': ["要点", "结论"],
                }
                comp = complements.get(verb, [""])[0]
                candidate = f"{verb} {topic} {comp}".strip()
            else:
                candidate = f"{verb} {pick_clause(clause)}"
        else:
            # 无动词时，仍然直接用用户子句作为主要候选
            candidate = pick_clause(clause)

        # 总是优先用用户句子（即使无动词）；仅当用户为空时才尝试助手
        if not candidate and text_user:
            candidate = text_user[:18]

        # 最后兜底：如果完全无用户句子，才用助手首句（且需过黑名单）
        if not candidate:
            assist_clause = pick_clause(text_assist)
            if assist_clause and not any(assist_clause.startswith(b) for b in assist_blacklist):
                candidate = assist_clause

        # 长度控制在 16–18 字范围（直接截断，不再追加省略号）
        candidate = candidate.strip()
        candidate = candidate[:18]

        # 强制最短长度避免太短
        candidate = candidate.strip()
        if len(candidate) == 0:
            return default_title

        return candidate

    def create_session(self, user_id="default_user", title=None, prompt=None):
        """创建新的对话会话"""
        if not title:
            title = self._derive_title(prompt)

        title = self._strip_trailing_ellipsis(title)

        # 移除会话去重逻辑，确保每次都创建新会话
        # 之前的逻辑会导致10分钟内相同标题的会话被合并，用户体验不佳

        # 创建新会话
        session_id = str(uuid.uuid4())
        conversation = Conversation(
            session_id=session_id,
            user_id=user_id,
            title=title
        )

        session = SessionLocal()
        try:
            session.add(conversation)
            session.commit()
            logger.info(f"✅ 会话已创建: {session_id} - {title}")
            return session_id
        except Exception as e:
            session.rollback()
            logger.error(f"❌ 会话创建失败: {e}")
            raise
        finally:
            session.close()

    def add_message(self, session_id, role, content, image_path=None):
        """添加消息到对话会话"""
        session = SessionLocal()
        try:
            message = Message(
                session_id=session_id,
                role=role,
                content=content,
                image_path=image_path
            )
            session.add(message)
            session.commit()

            # 更新会话的最后更新时间
            conversation = session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()
            if conversation:
                conversation.updated_at = datetime.now()
                session.commit()

            return message.id
        finally:
            session.close()

    def get_history(self, session_id, limit=10):
        """获取对话历史"""
        session = SessionLocal()
        try:
            # 强制刷新，确保获取最新数据
            session.expire_all()

            messages = session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(
                Message.created_at.desc(),
                Message.id.desc()
            ).limit(limit).all()

            # 反转顺序，使最早的消息在前
            messages.reverse()

            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "created_at": m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "image_path": (m.image_path if hasattr(m, 'image_path')
                                   else None)
                }
                for m in messages
            ]
        finally:
            session.close()

    def delete_message_and_following(self, message_id):
        """删除指定消息及其之后的所有消息"""
        session = SessionLocal()
        try:
            # 查找目标消息
            target_msg = session.query(Message).filter(
                Message.id == message_id
            ).first()

            if not target_msg:
                return False

            # 删除该会话中，创建时间晚于等于该消息的所有消息
            # 注意：使用 >= 包含目标消息本身
            session.query(Message).filter(
                Message.session_id == target_msg.session_id,
                Message.created_at >= target_msg.created_at
            ).delete(synchronize_session=False)

            session.commit()
            return True
        except Exception as e:
            print(f"删除消息失败: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_recent_sessions(self, user_id="default_user", limit=None):
        """获取最近的对话会话"""
        session = SessionLocal()
        try:
            # 强制刷新,确保看到最新数据
            session.expire_all()

            query = session.query(Conversation).filter(
                Conversation.user_id == user_id
            ).order_by(Conversation.updated_at.desc())

            if limit is not None:
                query = query.limit(limit)

            sessions = query.all()
            logger.info(
                f"📋 get_recent_sessions: user_id={user_id}, "
                f"limit={limit}, 查询到 {len(sessions)} 条会话"
            )
            if sessions:
                logger.info(
                    f"   最新会话: {sessions[0].title} - "
                    f"{sessions[0].updated_at}"
                )
                # DEBUG: 显示最新5条会话ID
                logger.info(
                    f"   最新5条ID: "
                    f"{[s.session_id[:8] for s in sessions[:5]]}"
                )

            return [
                {
                    "session_id": s.session_id,
                    "title": self._strip_trailing_ellipsis(s.title),
                    "pinned": getattr(s, 'pinned', False),  # v0.8.1
                    "created_at": s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "updated_at": s.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                }
                for s in sessions
            ]
        except Exception as e:
            logger.error(f"❌ 获取会话列表失败: {e}")
            session.rollback()
            return []
        finally:
            session.close()

    def delete_session(self, session_id):
        """删除对话会话及其消息"""
        session = SessionLocal()
        try:
            # 删除消息
            session.query(Message).filter(
                Message.session_id == session_id
            ).delete()

            # 删除会话
            session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).delete()

            session.commit()
        finally:
            session.close()

    def update_session_title(self, session_id, new_title):
        """更新会话标题"""
        session = SessionLocal()
        try:
            conversation = session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()

            if conversation:
                conversation.title = self._strip_trailing_ellipsis(new_title)
                conversation.updated_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()

    def update_session_pinned(self, session_id, pinned):
        """更新会话置顶状态"""
        session = SessionLocal()
        try:
            conversation = session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()

            if conversation:
                conversation.pinned = pinned
                conversation.updated_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()

    def get_session_stats(self, session_id):
        """获取会话统计信息"""
        from sqlalchemy import func
        session = SessionLocal()
        try:
            conversation = session.query(Conversation).filter(
                Conversation.session_id == session_id
            ).first()

            if not conversation:
                return None

            message_count = session.query(func.count(Message.id)).filter(
                Message.session_id == session_id
            ).scalar()

            return {
                "session_id": session_id,
                "title": self._strip_trailing_ellipsis(conversation.title),
                "message_count": message_count,
                "created_at": conversation.created_at.strftime(
                    '%Y-%m-%d %H:%M:%S'
                ),
                "updated_at": conversation.updated_at.strftime(
                    '%Y-%m-%d %H:%M:%S'
                )
            }
        finally:
            session.close()
