"""
v0.6.0 Phase 3 - AI能力增强

Day 1-2: 意图识别优化
- 多工具协同调用
- 工具调用失败智能重试
- 上下文感知增强
- 工具选择置信度评分
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any]
    priority: int = 0  # 执行优先级（数字越大越优先）
    depends_on: Optional[str] = None  # 依赖的工具名
    confidence: float = 1.0  # 置信度 0-1


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time: float = 0.0


class EnhancedToolSelector:
    """增强的工具选择器"""

    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        self.retry_strategies = {
            'search': self._retry_search,
            'weather': self._retry_weather,
            'file': self._retry_file,
        }

    def analyze_intent(self, prompt: str, context: Dict[str, Any]) -> List[ToolCall]:
        """
        分析用户意图，支持多工具协同

        Args:
            prompt: 用户输入
            context: 上下文信息（历史、记忆等）

        Returns:
            工具调用列表（按优先级排序）
        """
        tool_calls = []

        # 1. 快速规则匹配（高优先级工具）
        quick_matches = self._quick_match_tools(prompt)
        tool_calls.extend(quick_matches)

        # 2. AI深度分析（复杂意图）
        if not quick_matches or self._needs_deep_analysis(prompt):
            ai_matches = self._ai_analyze_tools(prompt, context)
            tool_calls.extend(ai_matches)

        # 3. 去重和排序
        tool_calls = self._deduplicate_tools(tool_calls)
        tool_calls.sort(key=lambda x: x.priority, reverse=True)

        return tool_calls

    def _quick_match_tools(self, prompt: str) -> List[ToolCall]:
        """快速规则匹配"""
        matches = []
        prompt_lower = prompt.lower()

        # 搜索工具（最高优先级）
        search_keywords = [
            '搜索', '查一下', '找一下', '搜一下',
            '最新', '新闻', '资讯', '发布',
            'iphone 17', 'iphone17', '什么时候'
        ]

        # 排除天气相关的查询，让它们进入深度分析
        weather_keywords = ['天气', '气温', '温度', '下雨', '下雪', '预报']
        is_weather_query = any(kw in prompt_lower for kw in weather_keywords)

        if any(kw in prompt_lower for kw in search_keywords) and not is_weather_query:
            matches.append(ToolCall(
                tool_name='search',
                parameters={'query': prompt},
                priority=100,
                confidence=0.95
            ))

        # 天气工具 - 移除快速匹配，交给LLM处理以支持从记忆中提取城市
        # weather_keywords = ['天气', '温度', '下雨', '下雪', '预报']
        # if any(kw in prompt_lower for kw in weather_keywords):
        #     matches.append(ToolCall(
        #         tool_name='weather',
        #         parameters={'query_type': 'now'},
        #         priority=80,
        #         confidence=0.9
        #     ))

        # 文件工具 - 移除快速匹配，交给LLM处理以支持参数提取
        # file_keywords = ['文件', '读取', '写入', '保存', '打开']
        # if any(kw in prompt_lower for kw in file_keywords):
        #     matches.append(ToolCall(
        #         tool_name='file',
        #         parameters={'operation': 'list'},
        #         priority=70,
        #         confidence=0.85
        #     ))

        # 系统工具
        system_keywords = ['cpu', '内存', '磁盘', '系统信息']
        if any(kw in prompt_lower for kw in system_keywords):
            matches.append(ToolCall(
                tool_name='system_info',
                parameters={'info_type': 'all'},
                priority=60,
                confidence=0.9
            ))

        return matches

    def _needs_deep_analysis(self, prompt: str) -> bool:
        """判断是否需要AI深度分析"""
        # 复杂查询、多步骤任务需要深度分析
        indicators = [
            '帮我', '能不能', '可以吗', '如何', '怎么',
            '然后', '接着', '之后', '同时', '还有'
        ]
        return any(ind in prompt for ind in indicators)

    def _ai_analyze_tools(self, prompt: str, context: Dict[str, Any]) -> List[ToolCall]:
        """AI深度分析工具需求"""
        try:
            # 检测多步骤任务
            result = []
            if '然后' in prompt or '接着' in prompt:
                steps = prompt.split('然后')
                for i, step in enumerate(steps):
                    if '搜索' in step:
                        result.append(ToolCall(
                            tool_name='search',
                            parameters={'query': step.strip()},
                            priority=100 - i*10,
                            confidence=0.85,
                            depends_on=result[-1].tool_name if result else None
                        ))
                    elif '文件' in step or '保存' in step:
                        result.append(ToolCall(
                            tool_name='file',
                            parameters={'operation': 'write'},
                            priority=90 - i*10,
                            confidence=0.8,
                            depends_on=result[-1].tool_name if result else None
                        ))
            return result
        except Exception as e:
            print(f"AI深度分析失败: {e}")
            return []

    def _deduplicate_tools(self, tool_calls: List[ToolCall]) -> List[ToolCall]:
        """去重工具调用"""
        seen = set()
        unique_calls = []

        for call in tool_calls:
            if call.tool_name not in seen:
                seen.add(call.tool_name)
                unique_calls.append(call)
            else:
                # 保留置信度更高的
                for i, existing in enumerate(unique_calls):
                    if existing.tool_name == call.tool_name:
                        if call.confidence > existing.confidence:
                            unique_calls[i] = call
                        break

        return unique_calls

    def execute_with_retry(
        self,
        tool_call: ToolCall,
        max_retries: int = 3,
        user_id: str = "default_user",
        session_id: Optional[str] = None
    ) -> ToolResult:
        """
        执行工具调用，支持智能重试

        Args:
            tool_call: 工具调用请求
            max_retries: 最大重试次数
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            工具执行结果
        """
        import time
        import asyncio

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"执行工具 {tool_call.tool_name} "
                    f"(尝试 {attempt + 1}/{max_retries})"
                )

                start_time = time.time()

                # 执行工具
                # 使用 asyncio.run 执行异步方法
                # 注意：ToolRegistry.execute 参数名为 params
                result = asyncio.run(self.tool_manager.execute(
                    tool_name=tool_call.tool_name,
                    params=tool_call.parameters,
                    user_id=user_id,
                    session_id=session_id
                ))

                execution_time = time.time() - start_time

                # 检查结果
                if result.get('success'):
                    return ToolResult(
                        tool_name=tool_call.tool_name,
                        success=True,
                        data=result.get('data'),
                        execution_time=execution_time
                    )

                # 失败，尝试智能重试
                if attempt < max_retries - 1:
                    logger.warning(
                        f"工具执行失败: {result.get('error')}, 准备重试..."
                    )

                    # 应用重试策略
                    if tool_call.tool_name in self.retry_strategies:
                        retry_params = self.retry_strategies[tool_call.tool_name](
                            tool_call.parameters,
                            result
                        )
                        if retry_params:
                            tool_call.parameters = retry_params
                            logger.info(f"使用新参数重试: {retry_params}")

                    # 指数退避
                    wait_time = (2 ** attempt) * 0.5
                    time.sleep(wait_time)
                else:
                    # 最后一次尝试也失败
                    return ToolResult(
                        tool_name=tool_call.tool_name,
                        success=False,
                        data=None,
                        error=result.get('error', '未知错误')
                    )

            except Exception as e:
                logger.error(f"工具执行异常: {e}", exc_info=True)

                if attempt == max_retries - 1:
                    return ToolResult(
                        tool_name=tool_call.tool_name,
                        success=False,
                        data=None,
                        error=str(e)
                    )

        # 不应该到这里
        return ToolResult(
            tool_name=tool_call.tool_name,
            success=False,
            data=None,
            error='未知错误'
        )

    def _retry_search(
        self,
        params: Dict[str, Any],
        previous_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """搜索工具重试策略"""
        query = params.get('query', '')

        # 策略1: 简化查询
        simplified = query.replace('搜索', '').replace('查一下', '').strip()
        if simplified != query:
            return {'query': simplified}

        # 策略2: 添加引号精确搜索
        if '"' not in query:
            return {'query': f'"{query}"'}

        return None

    def _retry_weather(
        self,
        params: Dict[str, Any],
        previous_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """天气工具重试策略"""
        # 如果城市识别失败，尝试其他常见城市
        if '未找到城市' in str(previous_result.get('error', '')):
            # 可以从上下文推断城市
            return {'city': '北京', 'query_type': params.get('query_type', 'now')}

        return None

    def _retry_file(
        self,
        params: Dict[str, Any],
        previous_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """文件工具重试策略"""
        # 如果路径不存在，尝试相对路径
        path = params.get('path', '')
        if '不存在' in str(previous_result.get('error', '')):
            # 尝试添加files/前缀
            if not path.startswith('files/'):
                return {**params, 'path': f'files/{path}'}

        return None


class ContextEnhancer:
    """上下文增强器"""

    def __init__(self, memory_manager, conversation_manager):
        self.memory = memory_manager
        self.conversation = conversation_manager

    def enhance_context(
        self,
        prompt: str,
        session_id: str,
        history_limit: int = 10
    ) -> Dict[str, Any]:
        """
        增强上下文信息

        Returns:
            {
                'recent_history': [],  # 最近对话历史
                'relevant_memories': [],  # 相关记忆
                'user_preferences': {},  # 用户偏好
                'entity_context': {}  # 实体上下文
            }
        """
        context = {}

        # 1. 最近对话历史
        context['recent_history'] = self.conversation.get_history(
            session_id,
            limit=history_limit
        )

        # 2. 语义相关记忆
        context['relevant_memories'] = self._get_relevant_memories(prompt)

        # 3. 用户偏好
        context['user_preferences'] = self._get_user_preferences()

        # 4. 实体上下文（地点、人物等）
        context['entity_context'] = self._extract_entities(prompt, context)

        return context

    def _get_relevant_memories(self, prompt: str, limit: int = 5) -> List[str]:
        """获取语义相关的记忆"""
        try:
            if hasattr(self.memory, 'semantic_recall'):
                return self.memory.semantic_recall(
                    query=prompt,
                    tag="facts",
                    limit=limit,
                    min_score=0.3
                )
            else:
                # 降级到普通recall
                return self.memory.recall(tag="facts", limit=limit)
        except Exception as e:
            logger.warning(f"获取相关记忆失败: {e}")
            return []

    def _get_user_preferences(self) -> Dict[str, Any]:
        """获取用户偏好"""
        # TODO: 从行为分析数据中提取偏好
        return {
            'response_style': 'balanced',  # detailed, balanced, concise
            'notification_enabled': True,
            'language': 'zh-CN'
        }

    def _extract_entities(
        self,
        prompt: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """从上下文中提取实体信息"""
        entities = {
            'locations': [],  # 地点
            'persons': [],  # 人物
            'times': [],  # 时间
            'objects': []  # 物品
        }

        # 从记忆中提取常用实体
        memories = context.get('relevant_memories', [])
        for memory in memories:
            # 简单的实体识别（可以用NER模型增强）
            if '在' in memory or '住在' in memory:
                # 可能包含地点
                pass
            # TODO: 更完善的实体提取

        return entities


if __name__ == "__main__":
    # 测试代码
    print("✅ Enhanced Tool Selector 模块加载成功")
    print("包含功能:")
    print("  - 多工具协同调用")
    print("  - 工具调用失败智能重试")
    print("  - 上下文感知增强")
    print("  - 工具选择置信度评分")
