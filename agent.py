from backend.memory import MemoryManager
from backend.conversation import ConversationManager
from backend.behavior_analytics import BehaviorAnalyzer
from backend.proactive_qa import ProactiveQA  # v0.3.0 主动问答
from backend.pattern_learning import PatternLearner  # v0.3.0 模式学习
from backend.tool_manager import get_tool_registry  # v0.4.0 工具管理
from backend.enhanced_intent import EnhancedToolSelector, ContextEnhancer
from backend.dialogue_enhancer import DialogueEnhancer  # v0.6.0
from backend.task_manager import TaskManager  # v0.8.0 任务管理
from backend.error_handler import (
    retry_with_backoff, log_execution, handle_api_errors,
    logger
)
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import re
import asyncio  # v0.4.0 用于同步执行异步工具调用
import sys

# 将项目根目录添加到 sys.path，以便导入 tools 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class XiaoLeAgent:
    def __init__(self):
        self.memory = MemoryManager()
        self.conversation = ConversationManager()
        self.behavior_analyzer = BehaviorAnalyzer()  # v0.3.0 行为分析器
        self.proactive_qa = ProactiveQA()  # v0.3.0 主动问答分析器
        self.pattern_learner = PatternLearner()  # v0.3.0 模式学习器
        self.tool_registry = get_tool_registry()  # v0.4.0 工具注册中心

        # v0.6.0 Phase 3: AI能力增强
        self.enhanced_selector = EnhancedToolSelector(self.tool_registry)
        self.context_enhancer = ContextEnhancer(self.memory, self.conversation)
        self.dialogue_enhancer = DialogueEnhancer()  # Day 4: 对话质量

        # v0.8.0 任务管理器
        db_config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASS')
        }
        self.task_manager = TaskManager(db_config)

        # v0.8.0 任务执行器(延迟导入避免循环依赖)
        from backend.task_executor import TaskExecutor
        self.task_executor = TaskExecutor(
            self.task_manager, self.tool_registry
        )

        # 注册工具
        self._register_tools()

        # 支持多个AI平台
        self.api_type = os.getenv("AI_API_TYPE", "deepseek")

        # DeepSeek配置
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_url = "https://api.deepseek.com/chat/completions"

        # Claude配置
        self.claude_key = os.getenv("CLAUDE_API_KEY")

        self.model = self._get_model()
        self.client = self._init_client()

    def _register_tools(self):
        """注册所有可用工具"""
        try:
            from tools import (
                weather_tool, system_info_tool,
                time_tool, calculator_tool, reminder_tool,
                search_tool, file_tool, delete_memory_tool,
                task_tool, vision_tool, register_face_tool
            )

            # 注册工具
            self.tool_registry.register(weather_tool)
            self.tool_registry.register(system_info_tool)
            self.tool_registry.register(time_tool)
            self.tool_registry.register(calculator_tool)
            self.tool_registry.register(reminder_tool)  # v0.5.0 提醒工具
            self.tool_registry.register(search_tool)  # v0.5.0 搜索工具
            self.tool_registry.register(file_tool)  # v0.5.0 文件工具
            self.tool_registry.register(delete_memory_tool)  # v0.8.1 删除记忆
            self.tool_registry.register(task_tool)  # v0.8.2 任务工具
            self.tool_registry.register(vision_tool)  # v0.9.0 视觉工具
            self.tool_registry.register(register_face_tool)  # v0.9.1 人脸注册工具

            logger.info(
                f"✅ 工具注册完成，共 "
                f"{len(self.tool_registry.get_tool_names())} 个工具"
            )
        except Exception as e:
            logger.error(f"工具注册失败: {e}", exc_info=True)

    def _get_model(self):
        """根据API类型获取模型名称"""
        if self.api_type == "deepseek":
            return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        else:  # claude
            return os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    def _init_client(self):
        """初始化客户端"""
        if self.api_type == "deepseek":
            if not self.deepseek_key or \
               self.deepseek_key == "your_deepseek_api_key_here":
                logger.warning("⚠️  警告: 未配置 DEEPSEEK_API_KEY，使用占位模式")
                return None
            logger.info(f"✅ 使用 DeepSeek API ({self.model})")
            return "deepseek"

        elif self.api_type == "claude":
            if not self.claude_key or \
               self.claude_key == "your_claude_api_key_here":
                logger.warning("⚠️  警告: 未配置 CLAUDE_API_KEY，使用占位模式")
                # 尝试回退到 DeepSeek
                if self.deepseek_key and \
                   self.deepseek_key != "your_deepseek_api_key_here":
                    logger.info("↩️  回退到 DeepSeek（因缺少 Claude Key）")
                    self.api_type = "deepseek"
                    self.model = self._get_model()
                    logger.info(f"✅ 使用 DeepSeek API ({self.model})")
                    return "deepseek"
                return None
            try:
                from anthropic import Anthropic
                logger.info(f"✅ 使用 Claude API ({self.model})")
                return Anthropic(api_key=self.claude_key)
            except Exception as e:
                logger.error(f"⚠️  Claude初始化失败: {e}")
                # 尝试回退到 DeepSeek
                if self.deepseek_key and \
                   self.deepseek_key != "your_deepseek_api_key_here":
                    logger.info("↩️  回退到 DeepSeek（Claude 初始化失败）")
                    self.api_type = "deepseek"
                    self.model = self._get_model()
                    logger.info(f"✅ 使用 DeepSeek API ({self.model})")
                    return "deepseek"
                return None

        logger.warning(f"⚠️  未知的API类型: {self.api_type}")
        # 尝试回退到 DeepSeek
        if self.deepseek_key and \
           self.deepseek_key != "your_deepseek_api_key_here":
            logger.info("↩️  回退到 DeepSeek（未知 API 类型）")
            self.api_type = "deepseek"
            self.model = self._get_model()
            logger.info(f"✅ 使用 DeepSeek API ({self.model})")
            return "deepseek"
        return None

    def think(self, prompt, use_memory=True):
        """调用 AI API 进行思考"""
        # 如果没有配置 API，返回占位响应
        if not self.client:
            return f"（占位模式）你说的是：{prompt}"

        try:
            # 获取当前时间和星期
            now = datetime.now()
            current_datetime = now.strftime("%Y年%m月%d日 %H:%M")
            weekday_names = ['周一', '周二', '周三', '周四',
                             '周五', '周六', '周日']
            current_weekday = weekday_names[now.weekday()]

            # 构建系统提示
            system_prompt = (
                "你是小乐AI管家，一个诚实、友好的个人助手。\n\n"
                "核心原则：\n"
                "1. 你是对话助手，没有连接智能设备（无手环/摄像头/传感器）\n"
                "2. 只使用用户明确告诉你的信息和下方的记忆库内容\n"
                "3. 记忆库按时间倒序排列，最新信息在前，优先使用最新信息\n"
                "4. 如果记忆库没有相关信息，诚实说'您还没告诉我'\n"
                "5. 当用户告诉你新信息时，友好确认并记录\n"
                "6. 绝不编造数据、假装有设备、或推测未知信息\n"
                f"当前时间：{current_datetime}（{current_weekday}）\n"
            )

            # 添加历史记忆（智能检索）
            if use_memory:
                # 1. 获取最近5条记忆（时间相关）- 最新信息优先
                recent_memories = self.memory.recall(
                    tag="general", limit=5)

                # 2. 搜索关键信息（名字、生日等重要记忆）
                keywords = ['叫', '名字', '生日', '爱好', '喜欢']
                important_memories = []
                for kw in keywords:
                    mems = self.memory.recall(
                        tag="general", keyword=kw, limit=2)
                    important_memories.extend(mems)

                # 3. 合并去重：最近记忆在前（优先级高）
                all_memories = list(dict.fromkeys(
                    recent_memories + important_memories))[:8]

                if all_memories:
                    context = "记忆库（按时间倒序，最新在前）：\n" + \
                              "\n".join(all_memories)
                    system_prompt += f"\n\n{context}"

            # 根据API类型调用
            if self.api_type == "deepseek":
                reply = self._call_deepseek(system_prompt, prompt)
            elif self.api_type == "claude":
                reply = self._call_claude(system_prompt, prompt)
            else:
                reply = "未知的API类型"

            # 处理回复中的日期占位符（以防AI还是使用了）
            reply = self._process_date_placeholders(reply)

            # 注意：对话记录不应存入memories表，会导致AI把自己的回复当成事实
            # 如果需要记录对话，应使用conversation.add_message()

            return reply

        except Exception as e:
            error_msg = f"调用 AI API 时出错: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return f"抱歉，我遇到了一些问题：{str(e)}"

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(requests.Timeout, requests.ConnectionError)
    )
    @handle_api_errors
    @log_execution
    def _call_deepseek(self, system_prompt, user_prompt, max_tokens=512):
        """调用 DeepSeek API"""
        logger.info(f"调用 DeepSeek API - Prompt长度: {len(user_prompt)}")

        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.5,
            "max_tokens": max_tokens,
            "stream": False
        }

        response = requests.post(
            self.deepseek_url,
            headers=headers,
            json=data,
            timeout=60  # 增加超时时间以处理复杂问题
        )

        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        logger.info(f"DeepSeek API 响应成功 - 回复长度: {len(reply)}")
        return reply

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(Exception,)
    )
    @handle_api_errors
    @log_execution
    def _call_claude(self, system_prompt, user_prompt, max_tokens=1024):
        """调用 Claude API"""
        logger.info(f"调用 Claude API - Prompt长度: {len(user_prompt)}")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        reply = response.content[0].text
        logger.info(f"Claude API 响应成功 - 回复长度: {len(reply)}")
        return reply

    def _process_date_placeholders(self, text):
        """处理文本中的日期占位符"""
        current_date = datetime.now().strftime("%Y年%m月%d日")
        current_datetime = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        # 替换各种可能的日期占位符（支持{{}}和[]两种格式）
        replacements = {
            r'\{\{当前日期\}\}': current_date,
            r'\{\{当前时间\}\}': current_datetime,
            r'\{\{今天\}\}': current_date,
            r'\{\{date\}\}': current_date,
            r'\{\{datetime\}\}': current_datetime,
            r'\[当前日期\]': current_date,
            r'\[当前时间\]': current_datetime,
            r'\[具体时间\]': current_datetime,
            r'\[今天\]': current_date,
            r'\[date\]': current_date,
            r'\[datetime\]': current_datetime,
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _extract_and_remember(self, user_message):
        """
        智能提取用户消息中的关键事实并存储
        只有当用户主动告诉我们关键信息时才存储
        """
        if not self.client:
            return  # 占位模式不提取

        # v0.9.4: 对明显的“非事实类”请求跳过提取，避免不必要的LLM调用
        try:
            q = (user_message or '').strip()
            q_lower = q.lower()
            time_like = any(k in q for k in [
                '现在几点', '几点了', '几点', '当前时间', '现在时间',
                '今天几号', '今天日期', '今天星期几', '星期几', '周几'
            ])
            remind_like = any(k in q_lower for k in ['提醒', '闹钟'])
            task_like = any(k in q_lower for k in ['任务', '待办'])
            search_like = any(k in q_lower for k in [
                              '搜索', '查一下', '搜一下', '帮我找', '帮我查', '百度', '谷歌'])

            import re as _re
            expr = q.replace('＝', '=').replace('？', '?')
            is_math = _re.fullmatch(
                r"[\s\d\.+\-\*/\(\)]+[=\s?]*", expr) is not None

            if time_like or remind_like or task_like or search_like or is_math:
                return
        except Exception:
            pass

        # 让AI判断是否包含需要记住的关键事实
        extraction_prompt = f"""分析用户的这句话，判断是否包含需要长期记住的关键信息。

用户说："{user_message}"

如果包含以下类型的关键信息，请提取出来（只提取用户明确告知的事实）：
- 姓名、年龄、生日、性别
- **身体特征**（例如身高、体重、体型、视力等）
- 明确的爱好、兴趣（例如"我喜欢..."）
- 职业、工作
- 家庭成员（**特别注意**：如果是家人的信息，必须明确标注关系，如"儿子"、"女儿"、"姑娘"、"妻子"等，不要写"用户"）
- 重要日期
- **用户的纠正和反馈**（例如"不算晨读"、"不包括..."、"你记错了..."）
- **用户的偏好和规则**（例如"我不喜欢..."、"只算..."）
- **对AI回答的补充说明**（例如"实际上..."、"其实..."）
- **用户的观点、看法或经历**（如果包含值得记忆的个人故事或独特见解）
- **长期计划或正在进行的项目**（例如"我正在准备考试"、"最近在装修"）
- **地点或环境信息**（例如"我在上海"、"家里养了猫"）

**不要提取以下内容：**
1. **临时任务和提醒**（例如"提醒我..."、"帮我..."、"查询..."、"告诉我..."）
2. **一次性操作**（例如"搜索..."、"计算..."、"创建提醒..."）
3. **工具调用请求**（例如"设置闹钟"、"查天气"、"删除记忆"）
4. 闲聊内容（例如"今天天气好"、"你好"）

**重要规则：**
1. 只提取用户主动告诉的**长期有效**的信息，不要推测
2. **特别注意用户的纠正**：如果用户指出AI的错误（特别是关于名字、关系），这是最高优先级的重要信息
3. **区分主语**：家人的信息必须标注关系（如"儿子姓名：xxx"），不要写成"用户姓名"
4. **名字准确性**：如果涉及名字，必须逐字确认，不要搞混
5. 提取格式：简洁的陈述句，例如"用户姓名：张三"、"儿子学校：逸夫中学"、"统计课程数量时不算晨读"

请直接返回提取结果，如果没有需要记住的信息就返回"无"。"""

        try:
            if self.api_type == "deepseek":
                result = self._call_deepseek(
                    system_prompt="你是信息提取助手，专门识别和提取用户的关键个人信息。",
                    user_prompt=extraction_prompt
                )
            else:  # claude
                result = self._call_claude(
                    system_prompt="你是信息提取助手，专门识别和提取用户的关键个人信息。",
                    user_prompt=extraction_prompt
                )

            # 如果提取到了有效信息（不是"无"），进行校验与规范化后存储到记忆
            invalid_results = ["无", "无。", "None", "none", ""]
            if result and result.strip() not in invalid_results:
                extracted = result.strip()

                # 家庭成员姓名硬性保护（防止儿子/女儿姓名对调被写入facts）
                # 权威事实：女儿=高艺瑄，儿子=高艺篪
                conflict_patterns = [
                    r"女儿[：:，,\s]*.*高艺篪",
                    r"儿子[：:，,\s]*.*高艺瑄",
                ]
                import re as _re
                for _p in conflict_patterns:
                    if _re.search(_p, extracted):
                        logger.warning(
                            "⛔ 阻止写入冲突家庭姓名事实: %s", extracted
                        )
                        # 不写入冲突内容，直接返回
                        return

                # 表述规范化：将“女儿姓名：可儿”更正为“小名”以避免伪冲突
                extracted = extracted.replace("女儿姓名：可儿", "女儿小名：可儿")

                self.memory.remember(extracted, tag="facts")
                logger.info(f"✅ 提取并存储关键事实: {extracted}")
            else:
                logger.info(f"ℹ️ 无需存储: {user_message}")

        except Exception as e:
            # 提取失败不影响主流程
            logger.warning(f"⚠️ 信息提取失败: {e}")

    def _summarize_conversation(self, session_id, message_count=10):
        """
        定期对对话内容生成摘要并存储

        Args:
            session_id: 会话ID
            message_count: 每隔多少条消息生成一次摘要
        """
        if not self.client:
            return  # 占位模式不生成摘要

        try:
            # 获取本次会话的所有历史消息
            history = self.conversation.get_history(
                session_id, limit=message_count
            )

            if len(history) < 3:  # 太少不值得摘要
                return

            # 构建对话内容
            conversation_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '小乐'}: {msg['content']}"
                for msg in history
            ])

            # 让AI生成对话摘要
            summary_prompt = f"""请为以下对话生成一个简洁的摘要，重点记录：
1. 用户的状态和心情（如困、开心、担心等）
2. 讨论的主要话题
3. 重要的上下文信息（正在做什么、计划做什么等）
4. 用户的需求或问题

对话内容：
{conversation_text}

请用1-3句话总结，格式如："用户表示很困还在聊天，讨论了课程安排的问题。"
如果对话只是简单问候或没有实质内容，返回"无"。"""

            if self.api_type == "deepseek":
                summary = self._call_deepseek(
                    system_prompt="你是对话摘要助手，提取对话中的关键信息。",
                    user_prompt=summary_prompt
                )
            else:
                summary = self._call_claude(
                    system_prompt="你是对话摘要助手，提取对话中的关键信息。",
                    user_prompt=summary_prompt
                )

            # 存储摘要
            invalid_results = ["无", "无。", "None", "none", ""]
            if summary and summary.strip() not in invalid_results:
                date_str = datetime.now().strftime("%Y-%m-%d")
                self.memory.remember(
                    summary.strip(),
                    tag=f"conversation:{date_str}"
                )
                logger.info(f"📝 对话摘要已存储: {summary.strip()[:50]}...")

        except Exception as e:
            logger.warning(f"⚠️ 对话摘要生成失败: {e}")

    def act(self, command):
        """执行任务：思考 -> 记录 -> 输出"""
        thought = self.think(command, use_memory=True)

        # 额外记录到 task 标签
        self.memory.remember(
            f"执行任务：{command} => {thought}",
            tag="task"
        )

        return thought

    def chat(self, prompt, session_id=None, user_id="default_user",
             response_style="balanced", image_path=None,
             original_user_prompt=None):
        """
        v0.6.0: 支持上下文的对话方法（支持响应风格）

        Args:
            prompt: 用户消息
            session_id: 会话ID（None则创建新会话）
            user_id: 用户ID
            response_style: 响应风格 (concise/balanced/detailed/professional)
        """
        # 性能监控
        import time
        start_time = time.time()

        # 如果没有session_id，创建新会话
        logger.info(
            f"💬 chat() 开始 - session_id参数: {session_id}, type: {type(session_id)}")
        if not session_id:
            logger.info("🆕 session_id为空,准备创建新会话")
            session_id = self.conversation.create_session(
                user_id=user_id,
                title=prompt[:50] + "..." if len(prompt) > 50 else prompt
            )
            logger.info(f"✅ 新会话已创建,ID: {session_id}")
        else:
            logger.info(f"📖 使用现有会话: {session_id}")

        # v0.5.0: 检查未读提醒 (仅在有相关关键词时执行)
        pending_reminders = []
        reminder_keywords = ['提醒', 'remind', '任务', 'task', '待办']
        if any(kw in prompt.lower() for kw in reminder_keywords):
            try:
                from reminder_manager import get_reminder_manager
                reminder_mgr = get_reminder_manager()
                pending_reminders = reminder_mgr.get_pending_reminders(
                    user_id, limit=3)
                logger.info(f"⏰ 检查提醒耗时: {time.time() - start_time:.2f}s")
            except Exception as e:
                logger.warning(f"检查提醒失败: {e}")

        # 获取对话历史
        history = self.conversation.get_history(session_id, limit=5)
        logger.info(f"📚 加载历史耗时: {time.time() - start_time:.2f}s")

        # 立即保存用户消息，防止刷新丢失
        user_message = original_user_prompt if original_user_prompt else prompt
        user_msg_id = self.conversation.add_message(
            session_id, "user", user_message, image_path=image_path
        )

        precomputed_reply = None  # v0.9.3: 若命中直答，跳过后续LLM/工具流程

        # v0.4.0: 智能工具调用 - 先分析是否需要调用工具
        tool_result = None

        # v0.8.0: 优先检查是否有等待中的任务需要恢复
        task_result = self._check_and_resume_task(prompt, user_id, session_id)

        # v0.8.0: 任务关键词预检查 (优先级高于工具调用)
        task_keywords = [
            '创建任务', '添加任务', '新建任务',
            '帮我准备', '帮我整理', '帮我规划',
            '帮我安排', '帮我计划', '帮我组织'
        ]
        skip_tool_check = any(keyword in prompt for keyword in task_keywords)

        if task_result:
            # 如果成功恢复任务，跳过工具调用
            skip_tool_check = True
            tool_result = None

        # v0.6.0 Phase 3: 使用增强的意图识别
        context = {
            'recent_messages': history,
            'user_id': user_id,
            'session_id': session_id
        }

        # 如果有图片，添加到prompt中以便意图识别能看到
        intent_prompt = prompt
        if image_path:
            intent_prompt = f"{prompt}\n[系统提示：用户上传了图片 {image_path}，请优先考虑使用视觉工具分析]"
            context['image_path'] = image_path

        # v0.9.3: 直答规则（如儿子/女儿小名）优先，命中则跳过工具/意图分析
        try:
            direct = self._try_direct_family_fact_answer(prompt)
            if direct:
                precomputed_reply = direct
                skip_tool_check = True
                tool_result = None
        except Exception as e:
            logger.warning(f"直答规则执行失败: {e}")

        # v0.9.4: 进一步的快速直达（时间/日期/简单计算等）
        # 保护：当prompt含有视觉识别结果，或当前上下文有图片路径时，跳过时间直达。
        contains_vision_result = (
            isinstance(prompt, str) and "<vision_result>" in prompt
        )
        has_image_ctx = bool(image_path)

        ask_what_phrases = [
            "这是什么",
            "这张图是什么",
            "这张图片是什么",
            "这张照片是什么",
            "这是什么东西"
        ]
        base_query = original_user_prompt or prompt
        is_ask_what = any(p in base_query for p in ask_what_phrases)

        allow_quick_time = (
            precomputed_reply is None
            and not contains_vision_result
            and not has_image_ctx
            and not is_ask_what
        )

        if allow_quick_time:
            try:
                quick_reply = self._try_quick_direct_answer(base_query)
                if quick_reply:
                    precomputed_reply = quick_reply
                    skip_tool_check = True
                    tool_result = None
            except Exception as e:
                logger.warning("快速直达失败: %s", e)

        # 增强的意图识别与工具执行
        try:
            tool_calls = self.enhanced_selector.analyze_intent(
                intent_prompt, context)

            if tool_calls:
                for tool_call in tool_calls:
                    result = self.enhanced_selector.execute_with_retry(
                        tool_call, max_retries=2, user_id=user_id, session_id=session_id
                    )
                    if result.success:
                        tool_result = {
                            'success': True,
                            'data': result.data,
                            'tool_name': result.tool_name
                        }
                        break

            if not tool_result:
                tool_result = self._auto_call_tool(
                    intent_prompt, user_id, session_id)
        except Exception as e:
            logger.warning(f"增强工具调用失败: {e}")
            try:
                tool_result = self._auto_call_tool(
                    intent_prompt, user_id, session_id)
            except Exception as e2:
                logger.warning(f"旧工具调用也失败: {e2}")

        # v0.8.0: 任务识别和执行
        # 如果已经成功执行了工具，且没有明确的任务关键词，则跳过复杂任务识别（避免重复执行）
        if not task_result and (not tool_result or not tool_result.get('success')):
            try:
                # 识别是否为复杂任务
                task_check = self.identify_complex_task(prompt, user_id)
                if task_check.get('is_task', False):
                    confidence = task_check.get('confidence', 0)
                    if confidence >= 0.7:
                        # 检查最近是否有相同任务（防止重复创建）
                        recent_tasks = self.task_manager.get_tasks_by_user(
                            user_id, limit=5
                        )
                        is_duplicate = False
                        for t in recent_tasks:
                            # 检查1分钟内创建的同名任务
                            # 注意：created_at可能是字符串或datetime
                            created_at = t['created_at']
                            if isinstance(created_at, str):
                                try:
                                    created_at = datetime.fromisoformat(
                                        created_at
                                    )
                                except ValueError:
                                    continue

                            # 简单的去重逻辑
                            if (t['title'] == task_check['title'] and
                                    (datetime.now() - created_at).total_seconds() < 60):
                                is_duplicate = True
                                break

                        if is_duplicate:
                            logger.info(f"跳过重复任务创建: {task_check['title']}")
                            task_result = {
                                'success': False,
                                'error': '任务已存在，请勿重复创建'
                            }
                        else:
                            logger.info(
                                f"识别到复杂任务(置信度:{confidence}): "
                                f"{task_check.get('title')}"
                            )

                            # 拆解任务
                            decompose_result = self.decompose_task(
                                task_title=task_check['title'],
                                task_description=task_check.get(
                                    'description', ''),
                                user_id=user_id
                            )

                        if decompose_result.get('success'):
                            # 创建任务
                            task_id = self.task_manager.create_task(
                                user_id=user_id,
                                session_id=session_id,
                                title=task_check['title'],
                                description=task_check.get('description', ''),
                                priority=decompose_result.get('priority', 0)
                            )

                            if task_id:
                                # 创建步骤
                                for step in decompose_result.get('steps', []):
                                    self.task_manager.create_step(
                                        task_id=task_id,
                                        step_num=step.get('step_num', 0),
                                        description=step.get(
                                            'description', ''),
                                        action_type=step.get('action_type'),
                                        action_params=step.get('action_params')
                                    )

                                # 执行任务
                                task_result = self.task_executor.execute_task(
                                    task_id=task_id,
                                    user_id=user_id,
                                    session_id=session_id
                                )

                                logger.info(f"任务执行结果: {task_result}")
            except Exception as e:
                logger.warning(f"任务处理失败: {e}", exc_info=True)

        # 如果是视觉工具的结果，保存到记忆
        if (tool_result and tool_result.get('success') and
                tool_result.get('tool_name') == 'vision_analysis'):
            try:
                data = tool_result.get('data', {})
                description = data.get('description', '')
                face_info = data.get('face_info', '')

                # 组合完整描述
                full_content = f"{face_info}\n{description}".strip()

                if full_content:
                    # 提取文件名作为标签的一部分
                    filename = (
                        os.path.basename(image_path)
                        if image_path else 'unknown'
                    )

                    # 保存记忆，使用 image:filename 标签，并关联图片路径
                    self.memory.remember(
                        full_content,
                        tag=f"image:{filename}",
                        image_path=image_path
                    )
                    logger.info(f"✅ 已保存图片记忆: {filename}")
            except Exception as e:
                logger.warning(f"保存图片记忆失败: {e}")

        # v0.6.0: 调用 AI 生成回复（带上下文、工具结果和响应风格）
        if precomputed_reply is not None:
            reply = precomputed_reply
        else:
            # 🔥 终极修复: 如果prompt包含vision_result,强制覆盖precomputed防止时间回复
            if '<vision_result>' in prompt or 'vision_result' in prompt.lower():
                logger.warning("🚨 检测到vision_result在prompt中,强制屏蔽时间回复!")
                # 直接从vision_result提取描述
                desc_start = prompt.find('<vision_result>')
                desc_end = prompt.find('</vision_result>')
                if desc_start != -1 and desc_end != -1:
                    vision_desc = prompt[desc_start+15:desc_end].strip()
                    if vision_desc and "我通过视觉能力识别到的图片内容：" in vision_desc:
                        vision_desc = vision_desc.split(
                            "我通过视觉能力识别到的图片内容：", 1)[-1].strip()
                    # 检查是否是"这是什么"类提问
                    user_q = original_user_prompt or ""
                    if any(p in user_q for p in ["这是什么", "这张图", "这个是什么"]):
                        reply = f"根据图片识别:\n\n{vision_desc}"
                        logger.info("✅ 使用vision直接回复,跳过LLM")
                    else:
                        # 其他情况走正常LLM,但添加强制指令
                        reply = self._think_with_context(
                            prompt, history, tool_result or task_result, response_style
                        )
                else:
                    reply = self._think_with_context(
                        prompt, history, tool_result or task_result, response_style
                    )
            else:
                reply = self._think_with_context(
                    prompt, history, tool_result or task_result, response_style
                )

        # v0.6.0 Phase 3 Day 4: 对话质量增强
        try:
            reply = self.dialogue_enhancer.enhance_response(
                reply, prompt, history, response_style
            )
        except Exception as e:
            logger.warning(f"对话质量增强失败: {e}")

        # v0.5.0: 如果有未读提醒，在回复前插入提醒
        if pending_reminders:
            reminder_text = self._format_reminders(pending_reminders)
            reply = reminder_text + "\n\n" + reply

        # 保存助手回复到会话表
        assistant_msg_id = self.conversation.add_message(
            session_id, "assistant", reply
        )

        # 智能提取：让AI判断是否有关键事实需要记住
        self._extract_and_remember(prompt)

        # v0.3.0: 模式学习（从用户消息中学习使用模式）
        try:
            self.pattern_learner.learn_from_message(
                user_id, prompt, session_id
            )
        except Exception as e:
            logger.warning(f"模式学习失败: {e}")

        # v0.3.0: 记录用户行为数据
        try:
            self.behavior_analyzer.record_session_behavior(user_id, session_id)
        except Exception as e:
            logger.warning(f"行为数据记录失败: {e}")

        # v0.6.0: 主动问答分析（检测是否需要追问）
        followup_info = None
        try:
            analysis = self.proactive_qa.analyze_conversation(
                session_id, user_id
            )
            if analysis.get("needs_followup"):
                questions = analysis.get("questions", [])
                if questions:
                    # 取置信度最高的问题
                    best_question = max(
                        questions, key=lambda x: x.get("confidence", 0)
                    )

                    # v0.6.0: 检查置信度是否达到阈值
                    confidence = best_question["confidence"]
                    threshold = self.proactive_qa.confidence_threshold

                    if confidence >= threshold:
                        # 生成追问
                        followup = (
                            self.proactive_qa.generate_followup_question(
                                best_question["question"],
                                best_question["missing_info"],
                                best_question.get("ai_response", "")
                            )
                        )
                        # 保存追问记录
                        question_id = (
                            self.proactive_qa.save_proactive_question(
                                session_id=session_id,
                                user_id=user_id,
                                original_question=best_question["question"],
                                question_type=best_question["type"],
                                missing_info=best_question["missing_info"],
                                confidence=confidence,
                                followup_question=followup
                            )
                        )
                        followup_info = {
                            "id": question_id,
                            "followup": followup,
                            "confidence": confidence
                        }
                        logger.info(
                            f"触发追问 (置信度: {confidence}% >= {threshold}%)"
                        )
                    else:
                        logger.debug(
                            f"置信度不足 ({confidence}% < {threshold}%)，跳过追问"
                        )
        except Exception as e:
            logger.warning(f"主动问答分析失败: {e}")

        # v0.6.1: 定期生成对话摘要（每5轮对话）
        try:
            history = self.conversation.get_history(session_id, limit=1)
            if history:
                # 获取当前会话的消息总数（简单估算：历史记录数量）
                message_count = len(
                    self.conversation.get_history(session_id, limit=100)
                )
                # 每5轮对话（10条消息）生成一次摘要
                if message_count > 0 and message_count % 10 == 0:
                    self._summarize_conversation(session_id, message_count=10)
        except Exception as e:
            logger.warning(f"对话摘要失败: {e}")

        result = {
            "session_id": session_id,
            "reply": reply,
            "user_message_id": user_msg_id,
            "assistant_message_id": assistant_msg_id
        }
        if followup_info:
            result["followup"] = followup_info

        # 如果有搜索结果，传递给前端用于展示"相关阅读"卡片
        if (tool_result and tool_result.get('success') and
                tool_result.get('tool_name') == 'search'):
            result["search_results"] = tool_result.get('results', [])

        # 性能监控：记录总耗时
        total_time = time.time() - start_time
        logger.info(f"⏱️ 响应完成，总耗时: {total_time:.2f}秒")
        if total_time > 3:
            logger.warning(f"⚠️ 响应较慢({total_time:.2f}s)，建议优化")

        return result

    def _try_direct_family_fact_answer(self, prompt: str):
        """
        v0.9.3: 对“儿子/女儿的小名/昵称/乳名”类问题进行规则直答，避免在大量记忆中被LLM忽略。

        命中条件：
        - 问句包含：儿子/女儿 且 包含：小名/昵称/乳名
        数据来源：
        - 从 facts 标签召回（优先 family 关键词），解析类似“儿子小名：乐儿”的格式。
        """
        q = (prompt or '').strip()
        if not q:
            return None

        q_lower = q.lower()
        # 命中关键词
        nick_words = ['小名', '昵称', '乳名']
        target = None
        if any(w in q for w in nick_words):
            if '儿子' in q:
                target = '儿子'
            elif '女儿' in q:
                target = '女儿'
            elif '孩子' in q or '小孩' in q:
                # 不明确对象时，不做直答
                target = None

        if not target:
            return None

        # 召回家庭相关facts
        try:
            keywords = [target, '小名', '昵称', '乳名']
            results = self.memory.recall_by_keywords(
                keywords, tag="facts", limit=20
            )
            contents = [m.get('content', '') for m in results]
        except Exception as e:
            logger.warning(f"直答召回失败: {e}")
            contents = []

        # 兜底：直接拉取全部facts后本地筛选
        if not contents:
            try:
                facts = self.memory.recall(tag="facts", limit=50)
                contents = facts
            except Exception:
                contents = []

        import re
        answer = None
        if target == '儿子':
            # 匹配：儿子小名：xxx 或 儿子的小名叫xxx
            patterns = [
                r"儿子小名[:：]\s*([\S ]{1,20})",
                r"儿子的?小名[叫是为][:：]?\s*([\S ]{1,20})"
            ]
        else:  # 女儿
            patterns = [
                r"女儿小名[:：]\s*([\S ]{1,20})",
                r"女儿的?小名[叫是为][:：]?\s*([\S ]{1,20})"
            ]

        for text in contents:
            t = (text or '').strip()
            if not t:
                continue
            for p in patterns:
                m = re.search(p, t)
                if m:
                    name = m.group(1).strip().replace(
                        '。', '').replace('\n', ' ')
                    # 剔除噪声占位
                    if any(bad in name for bad in ['未明确', '未知', '不详']):
                        continue
                    answer = name
                    break
            if answer:
                break

        if not answer:
            return None

        if target == '儿子':
            return f"根据我的记忆，您的儿子小名叫**{answer}**。"
        else:
            return f"根据我的记忆，您的女儿小名叫**{answer}**。"

    def _try_quick_direct_answer(self, prompt: str):
        """
        v0.9.4: 快速直答（绕过工具与LLM），进一步降低延迟。

        - 时间/日期/星期：本地计算后直接返回
        - 简单四则运算：本地安全求值（仅 + - * / () 和整数/小数）

        返回：命中则返回字符串答复，否则返回 None。

        ⚠️ 重要：此方法只应在纯文本对话时使用。
        调用前必须已确保没有图片上下文（image_path/vision_result）。
        """
        q = (prompt or '').strip()
        if not q:
            return None

        q_lower = q.lower()

        # 安全检查：如果prompt包含vision_result标记，绝不返回时间
        if '<vision_result>' in q or 'vision_result' in q_lower:
            return None

        # 1) 时间/日期/星期快速直答
        time_keywords = [
            '现在几点', '几点了', '几点', '当前时间', '现在时间',
            '今天几号', '今天日期', '日期', '今天星期几', '星期几', '周几'
        ]
        if any(kw in q for kw in time_keywords):
            now = datetime.now()
            date_str = now.strftime('%Y年%m月%d日')
            time_str = now.strftime('%H:%M')
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            weekday = weekday_names[now.weekday()]

            # 判定用户更关心时间/日期/星期
            if any(kw in q for kw in ['几点', '时间']):
                return f"现在是 {time_str}（{date_str}，{weekday}）。"
            if any(kw in q for kw in ['星期几', '周几']):
                return f"今天是{weekday}（{date_str} {time_str}）。"
            # 默认日期
            return f"今天是 {date_str}（{weekday}）{time_str}。"

        # 2) 简单计算器（安全求值）
        import re as _re
        expr = q.replace('＝', '=').replace('？', '?').replace('，', ',')
        # 识别可能的运算表达式
        # 仅允许数字、空格、小数点、()+-*/ 和末尾可选的 = 或 ?
        if _re.fullmatch(r"[\s\d\.+\-\*/\(\)]+[=\s?]*", expr) and any(op in expr for op in ['+', '-', '*', '/', '×', '÷']):
            safe = expr.replace('×', '*').replace('÷', '/')
            # 去掉尾部 = 或 ?
            safe = safe.rstrip('=? ').strip()

            try:
                import ast

                def _safe_eval(node):
                    if isinstance(node, ast.Expression):
                        return _safe_eval(node.body)
                    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                        left = _safe_eval(node.left)
                        right = _safe_eval(node.right)
                        if isinstance(node.op, ast.Add):
                            return left + right
                        if isinstance(node.op, ast.Sub):
                            return left - right
                        if isinstance(node.op, ast.Mult):
                            return left * right
                        if isinstance(node.op, ast.Div):
                            return left / right
                    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                        operand = _safe_eval(node.operand)
                        return +operand if isinstance(node.op, ast.UAdd) else -operand
                    if isinstance(node, ast.Num):
                        return node.n
                    if hasattr(ast, 'Constant') and isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                        return node.value
                    if isinstance(node, ast.Expr):
                        return _safe_eval(node.value)
                    raise ValueError('不支持的表达式')

                tree = ast.parse(safe, mode='eval')
                value = _safe_eval(tree)
                # 结果格式化：尽量简洁
                if isinstance(value, float):
                    # 去除无意义的小数位
                    text = f"{value:.10g}"
                else:
                    text = str(value)
                return f"结果：{text}"
            except Exception:
                # 失败则不拦截，交给工具/LLM
                return None

        return None

        # 3) 身份/版本/能力自述（极简直答）
        about_kws = ['你是谁', '关于你', '关于小乐', '你能做什么', '能做什么', '版本']
        if any(kw in q for kw in about_kws):
            try:
                tool_count = len(self.tool_registry.get_tool_names())
            except Exception:
                tool_count = 0
            app_ver = os.getenv('APP_VERSION', '0.8.0')
            model_name = self.model or 'unknown-model'
            # 简短直答，避免长段
            return (
                f"我是小乐 AI 管家。后端版本 {app_ver}，"
                f"可用工具 {tool_count} 个，当前模型 {model_name}。"
            )

    def _quick_intent_match(self, prompt):
        """
        v0.6.0: 快速意图匹配 - 无需AI调用的常见模式识别

        返回: None 或 {"needs_tool": bool, "tool_name": str, "parameters": dict}
        """
        prompt_lower = prompt.lower().strip()

        # 1. 时间查询 - 直接模式
        time_patterns = ['现在几点', '几点了', '当前时间', '现在时间', '今天日期', '今天几号']
        if any(p in prompt_lower for p in time_patterns):
            return {
                "needs_tool": True,
                "tool_name": "time",
                "parameters": {"format": "full"}
            }

        # 2. 系统信息 - 直接模式
        if any(word in prompt_lower for word in ['cpu', '内存', '磁盘', '系统信息']):
            info_type = "all"
            if 'cpu' in prompt_lower:
                info_type = "cpu"
            elif '内存' in prompt_lower:
                info_type = "memory"
            elif '磁盘' in prompt_lower:
                info_type = "disk"

            return {
                "needs_tool": True,
                "tool_name": "system_info",
                "parameters": {"info_type": info_type}
            }

        # 3. 计算器 - 简单数学表达式检测
        import re
        # 检测数学表达式 (数字 + 运算符)
        math_pattern = r'[\d\+\-\*/\(\)\s]+'
        if re.match(r'^\s*' + math_pattern + r'\s*[=?]?\s*$', prompt) and \
           any(op in prompt for op in ['+', '-', '*', '/', '×', '÷']):
            # 清理表达式
            expression = prompt.replace('=', '').replace('?', '').strip()
            expression = expression.replace('×', '*').replace('÷', '/')
            return {
                "needs_tool": True,
                "tool_name": "calculator",
                "parameters": {"expression": expression}
            }

        # 4. 搜索 - 明显的搜索意图
        search_keywords = [
            '搜索', '查询', '查一下', '搜一下', '找一下',
            '百度', '谷歌', '帮我找', '帮我查'
        ]

        # 扩展: 实时信息关键词 (需要上网查询的内容)
        realtime_keywords = [
            'iphone 17', 'iphone17', 'iphone 16', 'iphone16',
            '最新', '新闻', '消息', '资讯',
            '什么时候发布', '何时发布', '上市时间', '发售时间',
            '最新价格', '现在价格',
            '2025年', '2024年9月', '今年',
        ]

        # 检查是否包含搜索关键词
        has_search_keyword = any(kw in prompt_lower for kw in search_keywords)

        # 排除天气相关的查询，让它们进入深度分析
        weather_keywords = ['天气', '气温', '温度', '下雨', '下雪', '预报']
        if any(kw in prompt_lower for kw in weather_keywords):
            has_search_keyword = False

        # 排除提醒和任务相关的查询，让它们进入深度分析
        exclude_keywords = ['提醒', '闹钟', '日程', '待办', '任务', '计划', '安排']
        if any(kw in prompt_lower for kw in exclude_keywords):
            has_search_keyword = False

        # 检查是否包含实时信息关键词
        has_realtime_keyword = any(
            kw in prompt_lower for kw in realtime_keywords
        )

        # 调试日志
        if has_search_keyword or has_realtime_keyword:
            logger.info(
                f"🔍 快速规则匹配: 搜索={has_search_keyword}, "
                f"实时={has_realtime_keyword}, prompt='{prompt[:50]}'"
            )

        if has_search_keyword or has_realtime_keyword:
            # 如果是明确搜索,去除触发词;如果是实时信息,保留完整prompt
            if has_search_keyword and not has_realtime_keyword:
                query = prompt
                for kw in search_keywords:
                    query = query.replace(kw, '')
                query = query.strip()
            else:
                query = prompt.strip()

            # 确保有实际搜索内容
            if query and len(query) > 2:
                logger.info(f"✅ 触发搜索工具, query='{query[:50]}'")
                return {
                    "needs_tool": True,
                    "tool_name": "search",
                    "parameters": {"query": query, "max_results": 5}
                }
            else:
                logger.warning(f"⚠️  搜索query太短或为空: '{query}'")
                return None        # 5. 提醒 - 明确的提醒请求
        reminder_keywords = ['提醒我', '记得', '别忘了', '设置提醒', '定时提醒']
        if any(kw in prompt_lower for kw in reminder_keywords):
            # 需要AI解析时间和内容，返回None让AI处理
            return None

        # 5.5 查询/删除提醒 - 快速匹配
        query_keywords = [
            '查询', '查看', '我的', '有哪些', '列出'
        ]
        if any(kw in prompt_lower for kw in query_keywords):
            if '提醒' in prompt_lower or '闹钟' in prompt_lower:
                return {
                    "needs_tool": True,
                    "tool_name": "reminder",
                    "parameters": {"operation": "list", "status": "active"}
                }

        # 删除提醒
        if '删除' in prompt_lower and (
            '提醒' in prompt_lower or '闹钟' in prompt_lower
        ):
            import re
            # 提取提醒ID - 支持多种格式
            # 1. "删除ID为70的提醒" -> 70
            # 2. "删除提醒70" -> 70
            # 3. "删除编号70的提醒" -> 70
            id_match = (
                re.search(r'id[为是：:]*(\d+)', prompt_lower) or
                re.search(r'编号[为是：:]*(\d+)', prompt_lower) or
                re.search(r'(?:提醒|闹钟)[^\d]*?(\d+)', prompt) or
                re.search(r'(\d+)(?:号|个)?(?:提醒|闹钟)', prompt)
            )
            if id_match:
                reminder_id = int(id_match.group(1))
                logger.info(
                    f"✅ 快速匹配删除提醒: ID={reminder_id}, "
                    f"prompt='{prompt[:50]}'"
                )
                return {
                    "needs_tool": True,
                    "tool_name": "reminder",
                    "parameters": {
                        "operation": "delete",
                        "reminder_id": reminder_id
                    }
                }
            # 处理"删除这个/那个/所有提醒"等指代性表达
            elif any(
                ref in prompt_lower
                for ref in ['这个', '那个', '刚才', '上面', '所有', '全部', '全删']
            ):
                # 特殊处理：查询当前提醒数量
                # 如果只有1个，直接返回删除指令
                # 如果有多个，让AI列出让用户选择
                logger.info(f"🔍 指代性删除提醒: '{prompt[:50]}'")

                # 同步查询当前提醒数量
                try:
                    from reminder_manager import get_reminder_manager
                    mgr = get_reminder_manager()

                    # ReminderManager是同步方法，直接调用
                    reminders = mgr.get_user_reminders(
                        user_id="default_user",
                        enabled_only=True
                    )

                    if len(reminders) == 1:
                        # 只有1个提醒，直接删除
                        reminder_id = reminders[0]['reminder_id']
                        logger.info(
                            f"✅ 只有1个提醒，直接删除: ID={reminder_id}"
                        )
                        return {
                            "needs_tool": True,
                            "tool_name": "reminder",
                            "parameters": {
                                "operation": "delete",
                                "reminder_id": reminder_id
                            }
                        }
                    else:
                        # 多个提醒，让AI列出让用户选择
                        logger.info(
                            f"⚠️ 有{len(reminders)}个提醒，转交AI处理"
                        )
                        return None
                except Exception as e:
                    logger.warning(f"⚠️ 查询提醒失败: {e}")
                    return None  # 出错时让AI处理
            else:
                logger.warning(
                    f"⚠️ 删除提醒但未找到ID: '{prompt}'"
                )

        # 5.6 查询/删除任务 - 快速匹配
        if any(kw in prompt_lower for kw in query_keywords):
            if '任务' in prompt_lower or '待办' in prompt_lower:
                return {
                    "needs_tool": True,
                    "tool_name": "task",
                    "parameters": {"operation": "list"}
                }

        # 删除任务
        if '删除' in prompt_lower and (
            '任务' in prompt_lower or '待办' in prompt_lower
        ):
            logger.info(f"🔍 检测到删除任务请求: '{prompt[:80]}'")
            import re
            # 提取任务ID - 支持多种格式
            id_match = (
                re.search(r'id[为是：:]*(\d+)', prompt_lower) or
                re.search(r'编号[为是：:]*(\d+)', prompt_lower) or
                re.search(r'(?:任务|待办)[^\d]*?(\d+)', prompt) or
                re.search(r'(\d+)(?:号|个)?(?:任务|待办)', prompt)
            )
            logger.info(f"  ID匹配结果: {id_match}")
            if id_match:
                task_id = int(id_match.group(1))
                logger.info(
                    f"✅ 快速匹配删除任务: ID={task_id}, "
                    f"prompt='{prompt[:50]}'"
                )
                return {
                    "needs_tool": True,
                    "tool_name": "task",
                    "parameters": {
                        "operation": "delete",
                        "task_id": task_id
                    }
                }
            # 处理"删除这个/那个任务"等指代性表达
            elif any(
                ref in prompt_lower
                for ref in ['这个', '那个', '刚才', '上面', '所有', '全部', '全删']
            ):
                # 特殊处理：查询当前任务数量
                # 如果只有1个，直接返回删除指令
                # 如果有多个，让AI列出让用户选择
                logger.info(f"🔍 指代性删除任务: '{prompt[:50]}'")

                try:
                    from task_manager import get_task_manager
                    mgr = get_task_manager()

                    # TaskManager是同步方法，直接调用
                    # 查询所有任务（不限制状态），因为用户说"删除这个任务"通常指所有可见的
                    tasks = mgr.get_tasks_by_user(
                        user_id="default_user",
                        status=None  # 查询所有状态的任务
                    )

                    if len(tasks) == 1:
                        # 只有1个任务，直接删除
                        task_id = tasks[0]['id']  # 注意：键名是'id'，不是'task_id'
                        logger.info(
                            f"✅ 只有1个任务，直接删除: ID={task_id}"
                        )
                        return {
                            "needs_tool": True,
                            "tool_name": "task",
                            "parameters": {
                                "operation": "delete",
                                "task_id": task_id
                            }
                        }
                    else:
                        # 多个任务，让AI列出让用户选择
                        logger.info(
                            f"⚠️ 有{len(tasks)}个任务，转交AI处理"
                        )
                        return None
                except Exception as e:
                    logger.warning(f"⚠️ 查询任务失败: {e}")
                    return None  # 出错时让AI处理
            else:
                logger.warning(
                    f"⚠️ 删除任务但未找到ID: '{prompt}'"
                )

        # 6. 天气 - 智能快速匹配（尝试从记忆中提取城市）
        if '天气' in prompt_lower:
            # 尝试从记忆中查找城市信息
            try:
                # 1. 检查是否包含已知城市名
                # 这里简单列举一些常见城市，实际应该从WeatherTool获取
                common_cities = ['北京', '上海', '广州', '深圳',
                                 '天水', '秦州', '成都', '杭州', '武汉', '西安']
                for city in common_cities:
                    if city in prompt:
                        return {
                            "needs_tool": True,
                            "tool_name": "weather",
                            "parameters": {"city": city, "query_type": "now"}
                        }

                # 2. 如果没有明确城市，检查记忆库
                location_memories = self.memory.recall(tag="facts", limit=20)
                user_city = None
                for mem in location_memories:
                    # 简单的规则匹配提取城市
                    if "天水" in mem or "秦州" in mem:
                        user_city = "天水"
                        break
                    elif "深圳" in mem:
                        user_city = "深圳"
                        break
                    elif "北京" in mem:
                        user_city = "北京"
                        break

                if user_city:
                    logger.info(f"🔍 快速匹配: 从记忆中提取城市 '{user_city}'")
                    return {
                        "needs_tool": True,
                        "tool_name": "weather",
                        "parameters": {"city": user_city, "query_type": "now"}
                    }
            except Exception as e:
                logger.warning(f"天气快速匹配失败: {e}")

            # 如果无法快速匹配，返回None让AI处理
            return None

        # 7. 文件操作 - 需要AI精确解析
        file_keywords = [
            '读取文件', '写入文件', '文件列表', '搜索文件',
            '创建文件', '新建文件', '写文件', '查看文件', '列出文件'
        ]
        if any(kw in prompt_lower for kw in file_keywords):
            return None

        # 无匹配 - 可能是普通对话或需要AI分析
        return None

    def _get_style_instruction(self, style):
        """
        v0.6.0: 获取响应风格的指令

        Args:
            style: 响应风格 (concise/balanced/detailed/professional)

        Returns:
            str: 风格指令
        """
        styles = {
            'concise': '7. 响应风格：简洁模式 - 使用1-2句话简短回答，直接切中要点',
            'balanced': '7. 响应风格：均衡模式 - 提供适中长度的回答，既清晰又完整',
            'detailed': '7. 响应风格：详细模式 - 提供详细全面的解答，包含背景信息和例子',
            'professional': '7. 响应风格：专业模式 - 使用正式专业的语气，结构化表达',
            'voice_call': '7. 语音通话模式：像电话交谈，最多20字，避免寒暄、不要重复身份、直接回答或反问，禁止长段与列表'
        }
        return styles.get(style, styles['balanced'])

    def _get_llm_parameters(self, style):
        """
        v0.6.0: 根据响应风格获取LLM调用参数

        Args:
            style: 响应风格

        Returns:
            dict: {temperature, max_tokens, top_p}
        """
        params = {
            'concise': {
                'temperature': 0.3,
                'max_tokens': 512,
                'top_p': 0.8
            },
            'balanced': {
                'temperature': 0.5,
                'max_tokens': 2048,
                'top_p': 0.9
            },
            'detailed': {
                'temperature': 0.7,
                'max_tokens': 4096,
                'top_p': 0.95
            },
            'professional': {
                'temperature': 0.4,
                'max_tokens': 3072,
                'top_p': 0.85
            },
            'voice_call': {
                'temperature': 0.55,  # 略口语化但不跑题
                'max_tokens': 128,    # 极短回复
                'top_p': 0.85
            }
        }
        return params.get(style, params['balanced'])

    def _auto_call_tool(self, prompt, user_id, session_id):
        """
        v0.4.0: 智能工具调用
        分析用户消息，自动识别意图并调用相应工具
        """
        # 使用AI分析用户意图
        intent_analysis = self._analyze_intent(prompt)

        if not intent_analysis.get("needs_tool"):
            return None

        tool_name = intent_analysis.get("tool_name")
        params = intent_analysis.get("parameters", {})

        if not tool_name:
            return None

        # 添加调试日志
        logger.info(f"🔧 准备调用工具: {tool_name}")
        logger.info(f"📋 工具参数: {params}")

        # 调用工具（异步方法需要同步执行）
        try:
            # 使用asyncio.run()在同步上下文中执行异步工具调用
            result = asyncio.run(self.tool_registry.execute(
                tool_name=tool_name,
                params=params,
                user_id=user_id,
                session_id=session_id
            ))
            logger.info(
                f"✅ 工具调用成功: {tool_name} -> {result.get('success')}"
            )
            return result
        except Exception as e:
            logger.error(f"❌ 工具调用失败: {tool_name} - {e}")
            return None

    def _analyze_intent(self, prompt):
        """
        v0.6.0: 优化的意图识别算法
        使用AI分析用户消息，判断是否需要调用工具及具体参数

        改进点：
        1. 更清晰的工具分类和优先级
        2. 精简prompt减少token消耗
        3. 添加快速规则匹配（减少AI调用）
        4. 改进参数提取逻辑

        返回: {"needs_tool": bool, "tool_name": str, "parameters": dict}
        """
        # v0.6.0: 快速规则匹配 - 常见模式直接识别，无需AI
        quick_match = self._quick_intent_match(prompt)
        if quick_match:
            logger.info(f"✅ 快速规则匹配: {quick_match['tool_name']}")
            return quick_match

        # 获取可用工具列表
        tools_info = []
        for tool_name in self.tool_registry.get_tool_names():
            tool = self.tool_registry.get(tool_name)
            if tool and tool.enabled:
                params_desc = ", ".join([
                    f"{p.name}({p.param_type})"
                    for p in tool.parameters
                ])
                tools_info.append(
                    f"- {tool_name}: {tool.description}"
                    f"{' [参数: ' + params_desc + ']' if params_desc else ''}"
                )

        if not tools_info:
            return {"needs_tool": False}

        # 获取用户的位置信息（从记忆中查找）
        user_context = ""
        try:
            # 从facts标签中查找城市、地点相关信息
            location_memories = self.memory.recall(tag="facts", limit=20)

            # 新增：获取最近的文档记忆，让意图分析器知道用户最近上传了什么
            document_memories = []
            try:
                # 使用 recall_recent 获取最近30天的文档记忆
                recent_docs = self.memory.recall_recent(
                    hours=720, tag="document", limit=3
                )
                # 提取文件名和简要内容
                document_memories = []
                for mem in recent_docs:
                    # 从tag中提取文件名 document:filename
                    tag = mem.get('tag', '')
                    content = mem.get('content', '')
                    if ':' in tag:
                        filename = tag.split(':', 1)[1]
                    else:
                        filename = "unknown"
                    # 提取前150个字符
                    preview = content[:150].replace('\n', ' ')
                    document_memories.append(
                        f"已上传文档[{filename}]: {preview}..."
                    )
            except Exception as e:
                logger.warning(f"获取文档记忆失败: {e}")

            context_parts = []
            if location_memories:
                context_parts.append(
                    "用户背景信息（从记忆库提取）：\n" + "\n".join(location_memories)
                )

            # TODO: [Optimization] Current document preview (150 chars) is too short for detailed QA.
            # Consider implementing RAG or forcing file_tool usage for specific document queries
            # even if the summary doesn't contain the answer.
            # See docs/issues/20251124_DOCUMENT_RETRIEVAL_FAIL.md
            if document_memories:
                context_parts.append(
                    "最近上传的文档上下文：\n" + "\n".join(document_memories)
                )

            if context_parts:
                user_context = "\n\n" + "\n\n".join(context_parts)
                logger.info(
                    f"🔍 意图分析 - 注入上下文: {len(location_memories)}条记忆, "
                    f"{len(document_memories)}个文档"
                )
        except Exception as e:
            logger.warning(f"获取用户位置信息失败: {e}")

        # v0.6.0: 精简的意图分析 prompt（减少50% token消耗）
        analysis_prompt = f"""用户: "{prompt}"{user_context}

工具: {chr(10).join(tools_info)}

规则:
1. weather工具 - 需要城市名: city(城市名), query_type(now/3d/7d)
2. system_info - info_type(cpu/memory/disk/all)
3. time - format(full/date/time)
4. calculator - expression(数学表达式)
5. reminder - operation(create/list/delete/update), content(创建必填),
   time_desc(创建必填), reminder_id(删除/修改必填), status(active/all/completed)
   **删除/修改提醒时**:
   - 关键词："删除"、"取消"、"修改"、"改一下"、"推迟"、"延后"
   - 如用户说"删除/修改提醒72" -> 直接使用该ID
   - 如用户说"删除/修改这个/那个提醒"且**最近对话提到**具体提醒 -> 从上下文提取ID
   - 如果当前只有1个提醒且用户说"删除/修改这个" -> 直接操作那个提醒
   - 如果有多个提醒且无法确定ID -> 先list查询，告知用户提醒列表，让用户明确要操作哪个
   - **严禁**在用户想修改时创建新提醒！如果不确定ID，宁可先查询。
   - **重要**：如果用户反馈"提醒错乱"、"不对"、"不是这个"或提到"手动删除"，**必须**先使用 list 操作刷新列表！
   - **智能修改**：如果用户说"修改这个提醒"但你不知道ID，可以尝试不传reminder_id直接调用update，工具会自动检查是否只有唯一提醒。
6. task - operation(list/delete), task_id(删除必填), status(可选)
7. search - query(关键词), max_results(可选), timelimit(可选: d/w/m/y)
8. file - operation(read/write/list/search), path(路径),
   content(写入内容), pattern(搜索模式), recursive(可选)
   **文件操作映射**:
   - "创建/新建/写文件" -> operation="write"
   - "读取/查看/显示文件" -> operation="read"
   - "列出/查看目录/有哪些文件" -> operation="list"
   - **文档问答规则**：
     - 如果用户询问"最近上传的文档上下文"中已有的文档：
       - 询问**总结/概要** -> 不需要工具 (needs_tool=false)
       - 询问**具体细节/特定数据** -> **必须**调用file工具读取全文 (operation="read", path="文件名")
     - 如果用户询问未知的本地文件 -> 调用file工具查找/读取
9. vision_analysis - image_path(图片路径)
   - 当用户上传图片或询问"这张图"、"图片里"时使用
   - image_path通常在[系统提示]中提供
10. register_face - image_path(图片路径), person_name(人名)
   - 当用户明确说"这是xxx"、"记住这张脸是xxx"、"认识一下xxx"时使用
   - 必须同时提供图片和人名
11. 普通对话 -> needs_tool=false

**search工具优先级最高** - 以下情况必须使用:
- 用户明确要求"搜索"、"查一下"、"帮我找"
- 询问最新/实时信息(产品发布、新闻、价格)
- 涉及2024年9月后的信息(iPhone 17/16等新产品)
- 询问"什么时候发布"、"上市时间"等
- 你的知识可能过时的内容
- **例外**：如果用户是在询问"最近上传的文档上下文"中的内容，**不要**使用search工具，返回 needs_tool=false。

**查询/删除提醒** -> reminder工具
**查询/删除任务/待办** -> task工具

天气规则:
- 用户指定城市 -> 使用该城市
- 用户说"这里"、"我这"、"当地"或未指定城市 -> 必须从位置信息提取城市名
- 从位置信息提取城市名（只提取城市名如"深圳"、"天水"）
- 只有当无法获取任何城市信息时 -> needs_tool=false
- query_type: "明天"/"后天"=3d, "未来几天"/"本周"=7d, 其他=now

返回JSON（无markdown）:
{{
  "needs_tool": bool,
  "tool_name": "工具名或null",
  "parameters": {{"参数": "值"}},
  "reason": "简短理由"
}}"""

        try:
            if self.api_type == "deepseek":
                result = self._call_deepseek(
                    system_prompt="你是智能工具选择助手，精准识别用户意图并返回JSON格式分析结果。",
                    user_prompt=analysis_prompt
                )
            else:
                result = self._call_claude(
                    system_prompt="你是智能工具选择助手，精准识别用户意图并返回JSON格式分析结果。",
                    user_prompt=analysis_prompt
                )

            # 解析JSON结果
            import json
            # 清理可能的markdown代码块标记
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()

            analysis = json.loads(result)
            logger.info(f"意图分析: {analysis.get('reason', 'N/A')}")
            return analysis

        except Exception as e:
            logger.warning(f"意图分析失败: {e}")
            return {"needs_tool": False}

    def _think_with_context(self, prompt, history, tool_result=None,
                            response_style="balanced"):
        """
        v0.6.0: 带上下文的思考方法（支持响应风格）

        同时使用会话历史、长期记忆、工具结果和响应风格配置
        """
        if not self.client:
            return f"（占位模式）你说的是：{prompt}"

        try:
            # 🔥 最终防线: 检测vision_result直接返回
            if '<vision_result>' in prompt:
                logger.warning("🚨 _think_with_context检测到vision_result,直接提取!")
                desc_start = prompt.find('<vision_result>')
                desc_end = prompt.find('</vision_result>')
                if desc_start != -1 and desc_end != -1:
                    vision_desc = prompt[desc_start+15:desc_end].strip()
                    if "我通过视觉能力识别到的图片内容：" in vision_desc:
                        vision_desc = vision_desc.split(
                            "我通过视觉能力识别到的图片内容：", 1
                        )[-1].strip()
                    # 提取用户问题
                    user_q_match = prompt.find("用户问题：")
                    if user_q_match != -1:
                        user_q = prompt[user_q_match+5:].split('\n')[0].strip()
                        if any(kw in user_q for kw in ["什么", "啥", "是", "?"]):
                            return f"根据图片识别结果:\n\n{vision_desc}"
                    return f"这是图片识别内容:\n\n{vision_desc}"

            # 获取当前时间和星期
            now = datetime.now()
            current_datetime = now.strftime("%Y年%m月%d日 %H:%M")
            weekday_names = ['周一', '周二', '周三', '周四',
                             '周五', '周六', '周日']
            current_weekday = weekday_names[now.weekday()]

            # v0.6.0: 根据响应风格调整系统提示词
            style_instructions = self._get_style_instruction(response_style)

            if response_style == 'voice_call':
                # 极简系统提示以减少首token延迟
                system_prompt = (
                    "你是小乐，一个自然的语音助手。"
                    "用简短口语回复，最多20字，直接回答或追问。"
                    "禁止自报身份、禁止长段、禁止多句客套。"
                    "不要主动列功能/模式/操作列表，除非用户明确询问你能做什么。"
                    "纯确认类问题（例如是否听得见、是否在）只返回一个肯定/否定短句，可附用户昵称。"
                    f"当前时间：{current_datetime}（{current_weekday}）"
                )
            else:
                system_prompt = (
                    f"你是小乐AI管家，一个诚实、友好的个人助手。\n\n"
                    f"核心原则：\n"
                    f"1. **你拥有完整的工具能力**：可以查询/创建/删除提醒、任务、搜索信息、查天气、**读写文件**等\n"
                    f"   但没有连接智能设备（无手环/摄像头/传感器等物理设备）\n"
                    f"2. **数据优先级**（从高到低）：\n"
                    f"   ① 工具执行结果（最新实时数据，绝对准确）\n"
                    f"   ② 对话历史中的上下文信息\n"
                    f"   ③ 记忆库中的长期信息\n"
                    f"3. 当工具返回数据时，必须以工具数据为准，忽略任何过时的记忆或对话历史\n"
                    f"4. 记忆库按时间倒序排列，最新信息在前，优先使用最新信息\n"
                    f"5. 如果记忆库和对话历史都没有相关信息，诚实说'您还没告诉我'\n"
                    f"6. 绝不编造数据、假装有物理设备、或推测未知信息\n"
                    f"7. 【课程表回答规则】：\n"
                    f"   - 时段划分：上午=晨读+第1-4节，下午=第5-7节，晚上=课后辅导\n"
                    f"   - 只列出有课的时段，跳过\"无课\"的节次\n"
                    f"   - 格式：时段+课程名称，例如\"晨读：科学(6)、第4节：科学(5)\"\n"
                    f"   - 如果某个时间段完全没课，明确说明\n"
                    f"   - 示例：\"今天上午有晨读的科学(6)和第4节的科学(5)\"\n"
                    f"8. 【重要事实】：\n"
                    f"   - 必须严格区分家庭成员：女儿是【高艺瑄】，儿子是【高艺篪】\n"
                    f"   - 涉及名字、小名、家庭信息时，以【关键事实】或【facts】记忆为最高真理\n"
                    f"   - 记忆库中标记为【关键事实】的信息是最权威的，优先级高于其他所有信息\n"
                    f"{style_instructions}\n"
                    f"当前时间：{current_datetime}（{current_weekday}）\n"
                )

            # voice_call特殊：直接处理“能听见我说话吗”类确认问题，跳过LLM调用
            if response_style == 'voice_call':
                import re
                hearing_pattern = re.compile(
                    r"能(不能|否|可)?听[见到]?(我)?说?话吗[?？]*",
                    re.IGNORECASE
                )
                simple_prompt = (
                    prompt.strip()
                    .replace('。', '')
                    .replace('?', '？')
                )
                if hearing_pattern.search(simple_prompt):
                    # 尝试检索昵称
                    nickname = None
                    try:
                        facts_for_name = self.memory.recall(
                            tag="facts", limit=20
                        )
                        for fact in facts_for_name:
                            for key in [
                                "我叫", "叫我", "昵称是",
                                "我的名字是", "可以叫我"
                            ]:
                                if key in fact:
                                    idx = fact.find(key) + len(key)
                                    nickname = (
                                        fact[idx: idx + 10]
                                        .split('，')[0]
                                        .split('。')[0]
                                        .strip()
                                    )
                                    nickname = re.sub(
                                        r'^[是叫为]', '', nickname
                                    )
                                    break
                            if nickname:
                                break
                    except Exception as e:
                        logger.warning(f"昵称检索失败: {e}")
                    if not nickname or len(nickname) > 8:
                        nickname = "您"
                    return f"能听见你说话，{nickname}!"

            # v0.4.0: 如果有工具执行结果，添加到系统提示词
            if tool_result:
                logger.info(f"🔧 传递工具结果给AI: {tool_result}")
                if tool_result.get('success'):
                    # 格式化工具结果
                    tool_data = tool_result.get(
                        'data') or tool_result.get('result') or tool_result
                    logger.info(f"📦 提取的tool_data: {tool_data}")
                    if isinstance(tool_data, dict):
                        # 去除不需要显示的字段
                        display_data = {
                            k: v for k, v in tool_data.items()
                            if k not in ['success', 'user_id', 'session_id']
                        }
                        tool_info_text = str(display_data)
                    else:
                        tool_info_text = str(tool_data)

                    tool_info = (
                        f"\n\n📊 【实时工具执行结果 - 最高优先级数据】：\n"
                        f"{tool_info_text}\n\n"
                        f"🚨 强制规则：\n"
                        f"1. 这是刚刚查询的最新实时数据，绝对准确\n"
                        f"2. **必须完全基于此数据回答，严禁使用对话历史或记忆中的信息**\n"
                        f"3. 如果工具结果显示有数据，就说有；显示空，就说空\n"
                        f"4. 对话历史可能过时，完全忽略历史中关于该主题的所有内容\n"
                        f"5. 用自然友好的语言，直接根据上面的工具结果回答用户\n"
                        f"6. **必须保留来源链接**。对于搜索结果，必须在回答末尾逐一列出原始链接，严禁省略！格式如下：\n"
                        f"   \n"
                        f"   参考来源：\n"
                        f"   1. [标题](链接)\n"
                        f"   2. [标题](链接)\n"
                        f"   ..."
                    )
                    system_prompt += tool_info
                else:
                    # 工具执行失败，也要告知 AI
                    error_msg = tool_result.get('error', '未知错误')
                    tool_info = (
                        f"\n\n⚠️ 工具执行失败：\n"
                        f"错误信息：{error_msg}\n"
                        f"请告知用户你尝试了相关操作但遇到了问题，不要假装无法执行该功能。"
                    )
                    system_prompt += tool_info

            # 添加长期记忆到系统提示词
            # voice_call 模式：极度裁剪记忆以降低延迟，只在需要时保留关键信息
            if response_style == 'voice_call':
                schedule_keywords = ['课', '课程', '课程表', '第', '上午', '下午']
                need_schedule = any(kw in prompt for kw in schedule_keywords)
                # 尝试获取昵称相关的事实（用于个性化称呼）
                nickname_facts = []
                try:
                    raw_facts = self.memory.recall(tag="facts", limit=20)
                    for f in raw_facts:
                        if any(k in f for k in ["我叫", "叫我", "昵称", "名字"]):
                            nickname_facts.append(f[:60])
                except Exception as e:
                    logger.warning(f"voice_call 昵称记忆获取失败: {e}")
                schedule_memories = []
                if need_schedule:
                    try:
                        schedule_memories = self.memory.recall(
                            tag='schedule', limit=1
                        )
                    except Exception as e:
                        logger.warning(f"voice_call 课程表获取失败: {e}")
                # 组装精简记忆（昵称 + 课程表）
                trimmed_memories = []
                if nickname_facts:
                    trimmed_memories.append("昵称相关: " + nickname_facts[0])
                if schedule_memories:
                    trimmed_memories.extend(schedule_memories[:1])
                if trimmed_memories:
                    system_prompt += (
                        "\n\n记忆（精简）:\n" +
                        "\n".join(trimmed_memories)
                    )
                # 跳过后续大量记忆召回逻辑
                facts_memories = []
                semantic_memories = []
                image_memories = []
                document_memories = []
                conversation_memories = []
                recent_memories = []
            else:
                # 1. 优先获取 facts 标签的关键事实（用户主动告知的真实信息）
                facts_memories = self.memory.recall(tag="facts", limit=50)

            # 1.5 特别召回：家庭成员信息 (确保家人信息不被遗忘)
            family_memories = []
            try:
                family_keywords = [
                    '儿子', '女儿', '孩子', '老婆', '妻子',
                    '老公', '丈夫', '爸', '妈', '父亲', '母亲',
                    '姑娘', '闺女', '宝宝', '家人'
                ]
                # recall_by_keywords 返回字典列表
                family_results = self.memory.recall_by_keywords(
                    family_keywords, tag="facts", limit=20
                )
                family_memories = [m['content'] for m in family_results]
            except Exception as e:
                logger.warning(f"获取家庭成员记忆失败: {e}")

            # 2. 使用语义搜索查找相关记忆（不限标签，搜索所有记忆）
            semantic_memories = []
            if hasattr(self.memory, 'semantic_recall'):
                # 语义搜索用户问题相关的记忆（包括图片、事实等所有内容）
                semantic_memories = self.memory.semantic_recall(
                    query=prompt,
                    tag=None,  # 不限制标签，搜索所有记忆
                    limit=10,  # 减少语义搜索数量，避免淹没关键信息
                    min_score=0.05  # 降低阈值，增加召回
                )

            # 3. 获取最近的 image 记忆（课程表等重要信息）
            image_memories = []
            try:
                image_memories = self.memory.recall(tag="image", limit=3)
            except Exception as e:
                logger.warning(f"获取图片记忆失败: {e}")

            # 3.1 获取课程表记忆 (schedule) - 修复：增加对 schedule 标签的检索
            schedule_memories = []
            try:
                schedule_memories = self.memory.recall(tag="schedule", limit=1)
            except Exception as e:
                logger.warning(f"获取课程表失败: {e}")

            # 3.2 获取文档记忆 (document) - 新增：显式检索最近上传的文档
            document_memories = []
            try:
                document_memories = self.memory.recall(tag="document", limit=3)
            except Exception as e:
                logger.warning(f"获取文档记忆失败: {e}")

            # 4. 获取最近的对话摘要（了解之前聊了什么）
            conversation_memories = []
            try:
                conversation_memories = self.memory.recall(
                    tag="conversation", limit=10
                )
            except Exception as e:
                logger.warning(f"获取对话摘要失败: {e}")

            # 4. 获取最近的 general 记忆（补充上下文）
            recent_memories = self.memory.recall(tag="general", limit=3)

            # 5. 合并去重：图片记忆 > facts > 对话摘要 > 语义相关 > 最近记忆
            all_memories = []
            seen = set()

            # 🔝 定义过滤函数：排除过时的提醒相关记忆
            def is_outdated_reminder_memory(mem):
                """检查是否是过时的提醒记忆（应该被过滤掉）"""
                mem_lower = mem.lower()
                outdated_patterns = [
                    '删除了提醒', '提醒已删除', '提醒列表是空的',
                    '没有任何未完成的提醒', '提醒列表为空',
                    '已经删除了', '刚才删除了'
                ]
                return any(
                    pattern in mem_lower for pattern in outdated_patterns
                )

            # 🔝 最高优先级：图片记忆（课程表等重要信息）- 提到最前面！
            for mem in image_memories:
                if mem not in seen and not is_outdated_reminder_memory(mem):
                    all_memories.append(mem)
                    seen.add(mem)

            # 新增：课程表 (schedule) - 高优先级
            for mem in schedule_memories:
                if mem not in seen and not is_outdated_reminder_memory(mem):
                    all_memories.append(mem)
                    seen.add(mem)

            # 新增：文档总结 (document) - 高优先级
            for mem in document_memories:
                if mem not in seen and not is_outdated_reminder_memory(mem):
                    all_memories.append(mem)
                    seen.add(mem)

            # 新增：家庭成员信息 - 高优先级，加【关键事实】标记
            for mem in family_memories:
                if mem not in seen and not is_outdated_reminder_memory(mem):
                    # 给家庭成员信息加高亮标记，提高LLM注意力
                    highlighted_mem = f"【关键事实】{mem}"
                    all_memories.append(highlighted_mem)
                    seen.add(mem)  # seen中存原始内容，避免重复

            # 第二优先级：facts 标签（关键事实，但限制数量）
            facts_count = 0
            for mem in facts_memories:
                if (mem not in seen and facts_count < 30 and
                        not is_outdated_reminder_memory(mem)):  # 最多30条facts
                    all_memories.append(mem)
                    seen.add(mem)
                    facts_count += 1

            # 第三优先级：对话摘要（了解之前的对话上下文）
            for mem in conversation_memories:
                if (mem not in seen and len(all_memories) < 20 and
                        not is_outdated_reminder_memory(mem)):
                    all_memories.append(mem)
                    seen.add(mem)

            # 第四优先级：语义相关记忆（问题相关）
            # semantic_memories可能是字典列表，需要提取content
            for mem in semantic_memories:
                mem_content = (
                    mem if isinstance(mem, str)
                    else mem.get('content', str(mem))
                )
                if (mem_content not in seen and len(all_memories) < 20 and
                        not is_outdated_reminder_memory(mem_content)):
                    all_memories.append(mem_content)
                    seen.add(mem_content)

            # 第五优先级：最近记忆（补充上下文）
            for mem in recent_memories:
                if (mem not in seen and len(all_memories) < 40 and
                        not is_outdated_reminder_memory(mem)):
                    all_memories.append(mem)
                    seen.add(mem)

            # 调试：打印召回的记忆
            logger.info(f"📚 召回了 {len(all_memories)} 条记忆")
            for i, mem in enumerate(all_memories[:20], 1):  # 打印前20条
                preview = mem[:150] if isinstance(mem, str) else str(mem)[:150]
                logger.info(f"  记忆{i}: {preview}...")
                # 特别标记图片记忆（真正的课程表内容）
                if isinstance(mem, str) and len(mem) > 200:
                    # 课程表内容通常很长，且包含多个"节"和"课程"
                    course_indicators = mem.count('节') + mem.count('科学') + \
                        mem.count('数学') + mem.count('语文')
                    if course_indicators >= 3:  # 至少出现3次课程相关词
                        logger.info("    ⭐ [课程表内容]")

            # ⚠️ 关键修改：如果有工具结果，减少记忆干扰
            if tool_result and tool_result.get('success'):
                # 只保留课程表等基础信息，过滤掉所有对话记忆
                filtered_memories = []
                for mem in all_memories:
                    mem_lower = (
                        mem.lower() if isinstance(mem, str)
                        else str(mem).lower()
                    )
                    # 排除所有包含"提醒"、"删除"、"询问"的记忆
                    # v0.9.2: 移除了"对话"关键词，避免误删对话摘要
                    exclude_words = ['提醒', '删除', '询问', '刚才']
                    if not any(word in mem_lower for word in exclude_words):
                        filtered_memories.append(mem)
                        if len(filtered_memories) >= 10:  # v0.9.2: 增加到10条
                            break
                all_memories = filtered_memories
                logger.info(
                    f"⚠️ 有工具结果，精简记忆到 {len(all_memories)} 条，"
                    "避免历史干扰"
                )

            if all_memories:
                context = "记忆库（按时间倒序，最新在前）：\n" + \
                          "\n".join(all_memories)
                system_prompt += f"\n\n{context}"

                # 🔍 调试：检查"乐儿"是否在记忆中
                le_in_memories = [m for m in all_memories if '乐儿' in m]
                if le_in_memories:
                    logger.info(f"✅ 记忆中包含'乐儿': {le_in_memories[0][:100]}")
                else:
                    logger.warning("⚠️ 记忆中未找到'乐儿'！")

            # 构建消息列表（包含历史）
            messages = []

            # ⚠️ 关键修改：如果有工具结果，大幅减少历史对话数量
            if tool_result and tool_result.get('success'):
                # 只保留最近2条历史，避免被大量过时对话误导
                history_to_use = history[-2:] if len(history) > 2 else history
                logger.info(f"⚠️ 有工具结果，限制历史对话到最近 {len(history_to_use)} 条")
            else:
                history_to_use = history

            for msg in history_to_use:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            messages.append({"role": "user", "content": prompt})

            # v0.6.0: 根据API类型调用（传递响应风格）
            if self.api_type == "deepseek":
                return self._call_deepseek_with_history(
                    system_prompt, messages, response_style
                )
            elif self.api_type == "claude":
                return self._call_claude_with_history(
                    system_prompt, messages, response_style
                )

        except Exception as e:
            return f"抱歉，我遇到了一些问题：{str(e)}"

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(requests.Timeout, requests.ConnectionError)
    )
    @handle_api_errors
    @log_execution
    def _call_deepseek_with_history(
        self, system_prompt, messages, response_style="balanced"
    ):
        """
        v0.6.0: DeepSeek API 多轮对话（支持响应风格）
        """
        logger.info(f"调用 DeepSeek 多轮对话 - 消息数: {len(messages)}")

        # 🔍 调试日志：打印实际发送给AI的内容
        logger.info(f"📨 System Prompt 长度: {len(system_prompt)}")
        logger.info(f"📨 System Prompt 包含工具结果: {'工具执行结果' in system_prompt}")
        if messages:
            logger.info(f"📨 最后一条用户消息: {messages[-1]['content'][:100]}")

        # v0.6.0: 获取风格参数
        llm_params = self._get_llm_parameters(response_style)

        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + messages,
            "temperature": llm_params['temperature'],
            "max_tokens": llm_params['max_tokens'],
            "top_p": llm_params.get('top_p', 0.9)
        }

        response = requests.post(
            self.deepseek_url,
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        logger.info(
            f"DeepSeek 多轮对话响应成功 - 回复长度: {len(reply)}, "
            f"风格: {response_style}"
        )
        return reply

    def _format_reminders(self, reminders: list) -> str:
        """
        格式化提醒消息

        Args:
            reminders: 提醒列表

        Returns:
            格式化后的提醒文本
        """
        if not reminders:
            return ""

        reminder_texts = []
        for reminder in reminders:
            priority_emoji = {
                1: "🔴",  # 最高优先级
                2: "🟠",
                3: "🟡",
                4: "🟢",
                5: "⚪"   # 最低优先级
            }.get(reminder.get('priority', 3), "🔔")

            title = reminder.get('title', '提醒')
            content = reminder.get('content', '')

            reminder_texts.append(f"{priority_emoji} **{title}**：{content}")

        if len(reminders) == 1:
            header = "🔔 **提醒** "
        else:
            header = f"🔔 **你有 {len(reminders)} 条提醒** "

        return header + "\n" + "\n".join(reminder_texts)

    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(Exception,)
    )
    @handle_api_errors
    @log_execution
    @retry_with_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(Exception,)
    )
    @handle_api_errors
    @log_execution
    def _call_claude_with_history(
        self, system_prompt, messages, response_style="balanced"
    ):
        """
        v0.6.0: Claude API 多轮对话（支持响应风格）
        """
        logger.info(f"调用 Claude 多轮对话 - 消息数: {len(messages)}")

        # v0.6.0: 获取风格参数
        llm_params = self._get_llm_parameters(response_style)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=llm_params['max_tokens'],
            temperature=llm_params['temperature'],
            top_p=llm_params.get('top_p', 0.9),
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
        logger.info(
            f"Claude 多轮对话响应成功 - 回复长度: {len(reply)}, "
            f"风格: {response_style}"
        )
        return reply

    # ==================== v0.8.0 任务管理功能 ====================

    def identify_complex_task(self, user_input: str, user_id: str) -> dict:
        """
        识别用户输入是否为复杂任务

        Args:
            user_input: 用户输入
            user_id: 用户ID

        Returns:
            包含is_task和task_info的字典
        """
        prompt = f"""


请分析用户的输入是否为一个需要多步骤执行的复杂任务，或者是一个需要跟踪的待办事项。

任务的特征:
1. 需要多个步骤才能完成
2. 涉及多个工具或操作
3. 步骤之间有依赖关系
4. 需要一定时间完成
5. ** 涉及购物、办事、出行等需要规划或记录的事项**

用户输入: {user_input}

请以JSON格式回答:
{{
    "is_task": true/false,
    "confidence": 0.0-1.0,
    "title": "任务标题",
    "description": "任务描述",
    "reasoning": "判断理由"
}}

例子:
- "帮我准备周末的野餐" -> is_task: true(需要查天气、列物品、设提醒)
- "今天天气怎么样" -> is_task: false(单个查询)
- "提醒我明天9点开会" -> is_task: false(单个提醒)
- "帮我规划下周的学习计划" -> is_task: true(需要多步分析和安排)
- "去买杯冰美式" -> is_task: true(购物任务，可能需要导航或记录)
- "带份早餐" -> is_task: true(办事任务)
"""

        try:
            response = self._call_deepseek(
                system_prompt="你是任务分析助手，专门识别复杂任务。",
                user_prompt=prompt
            )
            # 提取JSON
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(
                    f"任务识别: {result.get('title', 'N/A')} - "
                    f"是否为任务: {result.get('is_task')}"
                )
                return result
            else:
                return {"is_task": False, "reasoning": "无法解析响应"}

        except Exception as e:
            logger.error(f"任务识别失败: {e}")
            return {"is_task": False, "reasoning": f"错误: {str(e)}"}

    def decompose_task(
        self,
        task_title: str,
        task_description: str,
        user_id: str
    ) -> dict:
        """
        将复杂任务拆解为多个步骤

        Args:
            task_title: 任务标题
            task_description: 任务描述
            user_id: 用户ID

        Returns:
            包含success和steps的字典
        """
        # 获取可用工具信息
        tools_info = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in self.tool_registry.list_tools()
        ])

        # 获取用户上下文信息（位置、偏好等）
        user_context = ""
        try:
            # 从facts标签中查找城市、地点相关信息
            location_memories = self.memory.recall(tag="facts", limit=20)
            if location_memories:
                user_context = (
                    "\n\n用户背景信息（从记忆库提取）：\n"
                    + "\n".join(location_memories)
                )
        except Exception as e:
            logger.warning(f"获取用户上下文失败: {e}")

        prompt = f"""
请将以下任务拆解为具体的执行步骤:

任务标题: {task_title}
任务描述: {task_description}
{user_context}

可用工具:
{tools_info}

要求:
1. 每个步骤要具体、可执行
2. 步骤之间要有逻辑顺序
3. ** 必须将所有变量（如"当前城市"、"明天"）替换为具体的值**
   - 如果知道用户在"天水"，weather工具的city参数必须填"天水"，绝不能填"当前城市"
   - 如果不知道城市，请默认使用"北京"或在步骤中要求用户提供
4. 需要调用工具的要标明工具名称和参数
   - reminder工具参数: content(必填), time_desc(必填), title(可选)
   - **重要：time_desc 请直接使用用户的自然语言描述（如"明天早上8点"），不要尝试转换为UTC时间或具体日期，工具会自动处理。**
5. 需要用户确认的要标明
6. 每个步骤包含: 序号、描述、操作类型、所需参数

以JSON格式返回:
{{
    "steps": [
        {{
            "step_num": 1,
            "description": "步骤描述",
            "action_type": "tool_call/user_confirm/wait/info",
            "action_params": {{
                "tool_name": "工具名",
                "params": {{}},
                "notes": "备注"
            }}
        }}
    ]
}}

示例任务"准备周末野餐"（假设用户在上海）:
{{
    "steps": [
        {{
            "step_num": 1,
            "description": "查询上海周末天气预报",
            "action_type": "tool_call",
            "action_params": {{
                "tool_name": "weather",
                "params": {{"city": "上海", "query_type": "7d"}},
                "notes": "确定天气情况"
            }}
        }},
        {{
            "step_num": 2,
            "description": "列出野餐所需物品清单",
            "action_type": "info",
            "action_params": {{
                "notes": "生成物品清单供用户参考"
            }}
        }},
        {{
            "step_num": 3,
            "description": "设置购物提醒",
            "action_type": "user_confirm",
            "action_params": {{
                "question": "是否需要设置购物提醒?",
                "if_yes": "tool_call:reminder"
            }}
        }},
        {{
            "step_num": 4,
            "description": "创建购物提醒",
            "action_type": "tool_call",
            "action_params": {{
                "tool_name": "reminder",
                "params": {{
                    "content": "购买野餐用品：餐垫、水果、饮料",
                    "time_desc": "明天早上9点"
                }},
                "notes": "用户确认后执行"
            }}
        }}
    ]
}}
"""

        try:
            response = self._call_deepseek(
                system_prompt=(
                    "你是任务拆解助手，专门将复杂任务拆解为执行步骤。"
                    "请只返回纯JSON数据，不要包含markdown标记。"
                ),
                user_prompt=prompt,
                max_tokens=4096
            )
            # 提取JSON
            import json
            import re

            # 尝试清理markdown标记
            cleaned_response = response.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response.split("```")[1]
                if cleaned_response.startswith("json"):
                    cleaned_response = cleaned_response[4:]
            cleaned_response = cleaned_response.strip()

            # 尝试直接解析
            try:
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试使用正则提取
                json_match = re.search(r'\{[\s\S]*\}', cleaned_response)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"JSON解析失败: {e}\n响应内容: {cleaned_response}")
                        return {'success': False, 'error': 'JSON格式错误'}
                else:
                    logger.error(f"未找到JSON内容\n响应内容: {cleaned_response}")
                    return {'success': False, 'error': '无法解析结果'}

            steps = result.get('steps', [])
            logger.info(f"任务拆解完成: 共 {len(steps)} 个步骤")
            return {
                'success': True,
                'steps': steps,
                'priority': result.get('priority', 0)
            }

        except Exception as e:
            logger.error(f"任务拆解失败: {e}")
            return {'success': False, 'error': str(e)}

    def _analyze_confirmation(self, prompt: str, step_description: str) -> str:
        """
        分析用户输入是否是对步骤的确认

        Returns:
            'confirmed', 'rejected', 'unrelated'
        """
        system_prompt = "你是意图判断助手。判断用户的输入是否对待确认步骤的确认。"
        user_prompt = f"""
待确认步骤: {step_description}
用户输入: "{prompt}"

请判断用户是:
1. 确认/同意(如"好的", "没问题", "确认", "是的") -> 返回 'confirmed'
2. 拒绝/取消(如"不要", "取消", "不行", "算了") -> 返回 'rejected'
3. 无关内容(如问天气, 聊其他话题) -> 返回 'unrelated'

只返回一个单词: confirmed / rejected / unrelated
"""
        try:
            if self.api_type == "deepseek":
                result = self._call_deepseek(system_prompt, user_prompt)
            else:
                result = self._call_claude(system_prompt, user_prompt)

            result = result.strip().lower()
            if 'confirmed' in result:
                return 'confirmed'
            if 'rejected' in result:
                return 'rejected'
            return 'unrelated'
        except Exception:
            return 'unrelated'

    def _check_and_resume_task(self, prompt, user_id, session_id):
        """检查并恢复等待中的任务"""
        import json
        try:
            # 获取等待中的任务
            tasks = self.task_manager.get_tasks_by_session(
                session_id, status='waiting'
            )
            if not tasks:
                return None

            task = tasks[0]

            # 获取等待的步骤
            steps = self.task_manager.get_task_steps(task['id'])
            waiting_step = next(
                (s for s in steps if s['status'] == 'waiting'), None
            )

            if not waiting_step:
                return None

            # 分析用户意图
            confirmation = self._analyze_confirmation(
                prompt, waiting_step['description']
            )

            if confirmation == 'unrelated':
                return None

            logger.info(f"任务恢复: 用户输入'{prompt}'被判定为 {confirmation}")

            if confirmation == 'confirmed':
                # 标记步骤为完成
                self.task_manager.update_step_status(
                    waiting_step['id'],
                    status='completed',
                    result=json.dumps(
                        {'confirmed': True, 'user_input': prompt}
                    )
                )
                # 恢复执行
                return self.task_executor.resume_task(
                    task['id'], user_id, session_id
                )
            else:
                # 用户拒绝，终止任务
                self.task_manager.update_step_status(
                    waiting_step['id'],
                    status='failed',
                    error_message=f'用户拒绝: {prompt}'
                )
                self.task_manager.update_task_status(
                    task['id'], status='failed'
                )
                return {
                    'success': False,
                    'error': f'任务已根据您的要求取消 (用户拒绝: {prompt})',
                    'task_id': task['id']
                }

        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return None
