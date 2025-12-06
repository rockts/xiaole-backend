"""
小乐AI工具模块

包含各种外部服务和系统操作工具
"""
from .weather_tool import weather_tool
from .system_tool import system_info_tool, time_tool, calculator_tool
from .reminder_tool import ReminderTool
from .search_tool import search_tool
from .file_tool import file_tool
from .delete_memory_tool import DeleteMemoryTool
from .task_tool import TaskTool
from .vision_tool import VisionTool, RegisterFaceTool

# 创建提醒工具实例
reminder_tool = ReminderTool()

# 创建删除记忆工具实例
delete_memory_tool = DeleteMemoryTool()

# 创建任务工具实例
task_tool = TaskTool()

# 创建视觉工具实例
vision_tool = VisionTool()
register_face_tool = RegisterFaceTool()

# 导出所有工具
__all__ = [
    'weather_tool',
    'system_info_tool',
    'time_tool',
    'calculator_tool',
    'reminder_tool',
    'search_tool',
    'file_tool',
    'delete_memory_tool',
    'task_tool',
    'vision_tool',
    'register_face_tool'
]
