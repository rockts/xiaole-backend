"""
工具调用框架

提供统一的工具接口、注册系统和执行管理。
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import logging
import json
from db_setup import SessionLocal, ToolExecution

logger = logging.getLogger(__name__)


class ToolParameter:
    """工具参数定义"""

    def __init__(
        self,
        name: str,
        param_type: str,
        description: str,
        required: bool = True,
        default: Any = None,
        enum: Optional[List[Any]] = None
    ):
        self.name = name
        self.param_type = param_type  # string, number, boolean, array, object
        self.description = description
        self.required = required
        self.default = default
        self.enum = enum

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """验证参数值"""
        # 必填参数检查
        if self.required and value is None:
            return False, f"参数 '{self.name}' 是必填项"

        # 如果不是必填且为None，使用默认值
        if value is None:
            return True, None

        # 类型检查
        type_map = {
            'string': str,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }

        expected_type = type_map.get(self.param_type)
        if expected_type and not isinstance(value, expected_type):
            return False, (
                f"参数 '{self.name}' 类型错误，"
                f"期望 {self.param_type}，实际 {type(value).__name__}"
            )

        # 枚举值检查
        if self.enum and value not in self.enum:
            return False, f"参数 '{self.name}' 值必须是 {self.enum} 之一"

        return True, None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'type': self.param_type,
            'description': self.description,
            'required': self.required,
            'default': self.default,
            'enum': self.enum
        }


class Tool(ABC):
    """工具基类

    所有工具都需要继承此类并实现execute方法
    """

    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.parameters: List[ToolParameter] = []
        self.category: str = "general"  # weather, search, system, etc.
        self.enabled: bool = True

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具

        Returns:
            {
                'success': bool,
                'result': Any,
                'error': Optional[str],
                'metadata': Optional[Dict]
            }
        """
        pass

    def validate_parameters(
        self, params: Dict[str, Any]
    ) -> tuple[bool, Optional[str], Dict[str, Any]]:
        """验证并处理参数"""
        validated_params = {}

        for param_def in self.parameters:
            value = params.get(param_def.name, param_def.default)

            # 验证参数
            is_valid, error_msg = param_def.validate(value)
            if not is_valid:
                return False, error_msg, {}

            # 使用默认值或实际值
            if value is not None:
                validated_params[param_def.name] = value
            else:
                validated_params[param_def.name] = param_def.default

        return True, None, validated_params

    def to_dict(self) -> Dict[str, Any]:
        """工具信息转字典"""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'enabled': self.enabled,
            'parameters': [p.to_dict() for p in self.parameters]
        }


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具"""
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")

        self._tools[tool.name] = tool
        logger.info(f"✅ 注册工具: {tool.name} ({tool.category})")

    def unregister(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"注销工具: {tool_name}")
            return True
        return False

    def get(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_name)

    def list_tools(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """列出所有工具"""
        tools = []
        for tool in self._tools.values():
            # 过滤条件
            if enabled_only and not tool.enabled:
                continue
            if category and tool.category != category:
                continue

            tools.append(tool.to_dict())

        return tools

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        task_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行工具并记录"""
        start_time = datetime.now()

        # 检查工具是否存在
        tool = self.get(tool_name)
        if not tool:
            return {
                'success': False,
                'error': f"工具 '{tool_name}' 不存在",
                'result': None
            }

        # 检查工具是否启用
        if not tool.enabled:
            return {
                'success': False,
                'error': f"工具 '{tool_name}' 已被禁用",
                'result': None
            }

        # 验证参数
        result = tool.validate_parameters(params)
        is_valid, error_msg, validated_params = result
        if not is_valid:
            return {
                'success': False,
                'error': f"参数验证失败: {error_msg}",
                'result': None
            }

        # 执行工具
        try:
            # 将 user_id 和 session_id 添加到执行参数中
            exec_params = {
                **validated_params,
                "user_id": user_id,
                "session_id": session_id
            }
            # 只有当task_id不为None时才添加（避免覆盖工具自己的task_id参数）
            if task_id is not None:
                exec_params["task_id"] = task_id

            result = await tool.execute(**exec_params)
            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录执行历史
            self._save_execution(
                tool_name=tool_name,
                user_id=user_id,
                session_id=session_id,
                params=validated_params,
                result=result,
                execution_time=execution_time
            )

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"工具 '{tool_name}' 执行失败: {e}", exc_info=True)

            error_result = {
                'success': False,
                'error': f"执行异常: {str(e)}",
                'result': None
            }

            # 记录失败的执行
            self._save_execution(
                tool_name=tool_name,
                user_id=user_id,
                session_id=session_id,
                params=validated_params,
                result=error_result,
                execution_time=execution_time
            )

            return error_result

    def _save_execution(
        self,
        tool_name: str,
        user_id: str,
        session_id: Optional[str],
        params: Dict[str, Any],
        result: Dict[str, Any],
        execution_time: float
    ) -> None:
        """保存执行记录到数据库"""
        try:
            session = SessionLocal()
            try:
                execution = ToolExecution(
                    tool_name=tool_name,
                    user_id=user_id,
                    session_id=session_id,
                    parameters=json.dumps(params, ensure_ascii=False),
                    result=json.dumps(result, ensure_ascii=False),
                    success=result.get('success', False),
                    error_message=result.get('error'),
                    execution_time=execution_time,
                    executed_at=datetime.now()
                )
                session.add(execution)
                session.commit()
                status = '成功' if result.get('success') else '失败'
                logger.info(
                    f"📝 记录工具执行: {tool_name} ({status}) "
                    f"- {execution_time:.2f}s"
                )
            finally:
                session.close()
        except Exception as e:
            logger.error(f"保存工具执行记录失败: {e}", exc_info=True)


# 全局工具注册中心
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册中心"""
    return tool_registry
