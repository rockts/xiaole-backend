"""
任务管理工具
支持查询和删除任务
"""
from backend.tool_manager import Tool, ToolParameter
import logging

logger = logging.getLogger(__name__)


class TaskTool(Tool):
    """任务管理工具 - 查询、删除任务"""

    def __init__(self):
        super().__init__()
        self.name = "task"
        self.description = "任务管理工具：创建、查询、修改、删除任务"
        self.category = "task"
        self.enabled = True
        self.parameters = [
            ToolParameter(
                name="operation",
                param_type="string",
                description=(
                    "操作类型：create(创建), list(查询), "
                    "update(修改), delete(删除)"
                ),
                required=True,
                default="list",
                enum=["create", "list", "update", "delete"]
            ),
            ToolParameter(
                name="task_id",
                param_type="number",
                description="任务ID（修改/删除时必填）",
                required=False
            ),
            ToolParameter(
                name="title",
                param_type="string",
                description="任务标题（创建时必填，修改时可选）",
                required=False
            ),
            ToolParameter(
                name="description",
                param_type="string",
                description="任务描述（创建/修改时可选）",
                required=False
            ),
            ToolParameter(
                name="status",
                param_type="string",
                description=(
                    "任务状态（查询时过滤，修改时可选）："
                    "pending(待处理), in_progress(进行中), waiting(等待), "
                    "completed(已完成), failed(失败), cancelled(已取消)"
                ),
                required=False,
                enum=[
                    "pending", "in_progress", "waiting",
                    "completed", "failed", "cancelled"
                ]
            ),
            ToolParameter(
                name="priority",
                param_type="number",
                description="优先级（创建/修改时可选，0-10，默认5）",
                required=False
            )
        ]

    async def execute(self, **kwargs) -> dict:
        """
        执行任务操作

        Args:
            **kwargs: 包含 operation, task_id, title, description,
                     status, priority, user_id, session_id
        """
        try:
            operation = kwargs.get("operation", "list")
            user_id = kwargs.get("user_id", "default_user")

            # 延迟导入避免循环依赖
            from task_manager import get_task_manager
            task_mgr = get_task_manager()

            if operation == "create":
                return await self._handle_create(task_mgr, user_id, kwargs)
            elif operation == "list":
                return await self._handle_list(task_mgr, user_id, kwargs)
            elif operation == "update":
                return await self._handle_update(task_mgr, kwargs)
            elif operation == "delete":
                return await self._handle_delete(task_mgr, kwargs)
            else:
                return {
                    "success": False,
                    "data": f"❌ 不支持的操作类型: {operation}"
                }

        except Exception as e:
            logger.error(f"任务操作失败: {e}")
            return {
                "success": False,
                "data": f"❌ 操作失败: {str(e)}"
            }

    async def _handle_create(self, mgr, user_id: str, kwargs) -> dict:
        """处理创建任务请求"""
        title = kwargs.get("title")
        if not title:
            return {
                "success": False,
                "data": "❌ 创建任务需要提供标题"
            }

        description = kwargs.get("description", "")
        priority = kwargs.get("priority", 5)
        session_id = kwargs.get("session_id", "")

        try:
            task_id = mgr.create_task(
                user_id=user_id,
                session_id=session_id,
                title=title,
                description=description,
                priority=int(priority) if priority else 5
            )

            if task_id:
                return {
                    "success": True,
                    "data": f"✅ 任务已创建 (ID: {task_id})\n📋 标题: {title}"
                }
            else:
                return {
                    "success": False,
                    "data": "❌ 创建任务失败"
                }
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return {
                "success": False,
                "data": f"❌ 创建失败: {str(e)}"
            }

    async def _handle_list(self, mgr, user_id: str, kwargs) -> dict:
        """处理查询请求"""
        status = kwargs.get("status")
        tasks = mgr.get_tasks_by_user(user_id, status=status, limit=10)

        if not tasks:
            status_text = f"({status})" if status else ""
            return {
                "success": True,
                "data": f"📭 你目前没有任务{status_text}。"
            }

        # 统计信息
        total_count = len(tasks)
        status_counts = {}
        for t in tasks:
            st = t['status']
            status_counts[st] = status_counts.get(st, 0) + 1

        # 格式化任务列表
        status_text = f"({status})" if status else ""
        lines = [f"📋 **你的任务列表{status_text}** (共{total_count}个)：\n"]

        for t in tasks:
            status_info = {
                'pending': ('⏳', '待处理'),
                'in_progress': ('▶️', '进行中'),
                'completed': ('✅', '已完成'),
                'failed': ('❌', '失败'),
                'waiting': ('⏸️', '等待中'),
                'cancelled': ('🚫', '已取消')
            }.get(t['status'], ('❓', '未知'))

            emoji, status_cn = status_info
            # 强调状态显示,避免标题中的"完成"等词被误解
            lines.append(
                f"- [ID:{t['id']}] **{emoji} {status_cn}** → {t['title']}"
            )

        # 添加统计摘要
        if not status:  # 只有查询全部任务时才显示分类统计
            lines.append("\n**状态统计**:")
            for st, count in status_counts.items():
                status_info = {
                    'pending': ('⏳', '待处理'),
                    'in_progress': ('▶️', '进行中'),
                    'completed': ('✅', '已完成'),
                    'failed': ('❌', '失败'),
                    'waiting': ('⏸️', '等待中'),
                    'cancelled': ('🚫', '已取消')
                }.get(st, ('❓', '未知'))
                emoji, status_text = status_info
                lines.append(f"  {emoji} {status_text}: {count}个")

        return {
            "success": True,
            "data": "\n".join(lines)
        }

    async def _handle_update(self, mgr, kwargs) -> dict:
        """处理更新任务请求"""
        task_id = kwargs.get("task_id")
        user_id = kwargs.get("user_id", "default_user")

        if not task_id:
            return {
                "success": False,
                "data": "❌ 修改任务需要提供 task_id"
            }

        # 检查任务是否存在
        task = mgr.get_task(int(task_id))
        if not task:
            return {
                "success": False,
                "data": f"❌ 任务不存在 (ID: {task_id})"
            }

        # 验证所有权
        if task.get('user_id') != user_id:
            return {
                "success": False,
                "data": f"❌ 无权修改此任务 (ID: {task_id})"
            }

        updates = []

        # 更新状态
        status = kwargs.get("status")
        if status:
            success = mgr.update_task_status(int(task_id), status)
            if success:
                status_text = {
                    'pending': '待处理',
                    'in_progress': '执行中',
                    'waiting': '等待中',
                    'completed': '已完成',
                    'failed': '失败',
                    'cancelled': '已取消'
                }.get(status, status)
                updates.append(f"状态 → {status_text}")

        # 更新标题和描述（需要扩展task_manager）
        # 暂时只支持状态更新，后续可扩展

        if updates:
            return {
                "success": True,
                "data": (
                    f"✅ 任务已更新 (ID: {task_id})\n"
                    f"📝 更新内容: {', '.join(updates)}"
                )
            }
        else:
            return {
                "success": False,
                "data": "❌ 没有可更新的内容"
            }

    async def _handle_delete(self, mgr, kwargs) -> dict:
        """处理删除请求"""
        task_id = kwargs.get("task_id")
        user_id = kwargs.get("user_id", "default_user")

        if not task_id:
            return {"success": False, "data": "❌ 删除任务需要提供 task_id"}

        # 验证任务存在和权限
        task = mgr.get_task(int(task_id))
        if not task:
            return {
                "success": False,
                "data": f"❌ 任务不存在 (ID: {task_id})"
            }

        # 验证所有权
        if task.get('user_id') != user_id:
            return {
                "success": False,
                "data": f"❌ 无权删除此任务 (ID: {task_id})"
            }

        # 执行删除
        success = mgr.delete_task(int(task_id))

        if success:
            return {"success": True, "data": f"✅ 任务已删除 (ID: {task_id})"}
        else:
            return {
                "success": False,
                "data": f"❌ 删除失败 (ID: {task_id})"
            }
