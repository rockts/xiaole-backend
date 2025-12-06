"""
记忆删除工具
允许用户通过对话删除数据库中的记忆
"""
from typing import Optional
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from backend.db_setup import Memory, SessionLocal
from backend.tool_manager import Tool, ToolParameter

logger = logging.getLogger(__name__)


class DeleteMemoryTool(Tool):
    """记忆删除工具 - 支持按关键词、时间范围、标签删除记忆"""

    def __init__(self, db=None):
        super().__init__()
        self.name = "delete_memory"
        self.category = "memory"  # 记忆管理类工具
        self.enabled = True
        self.db = db or SessionLocal()
        self.description = """删除数据库中的记忆。
支持的删除方式：
1. 按关键词删除：删除包含特定关键词的记忆
2. 按时间范围删除：删除最近N分钟/小时/天的记忆
3. 按标签删除：删除特定类型的记忆（如：对话、知识、任务等）
4. 组合条件删除：可以组合使用上述条件

参数：
- keywords: 关键词（可选），支持多个关键词用逗号分隔
- time_range: 时间范围（可选），格式如 "5分钟前"、"1小时前"、"昨天"
- tags: 标签（可选），支持多个标签用逗号分隔
- confirm: 是否确认删除（必须为 true 才会真正删除）

示例：
- 删除包含"错误信息"的记忆：{"keywords": "错误信息", "confirm": true}
- 删除最近5分钟的记忆：{"time_range": "5分钟前", "confirm": true}
- 删除对话类记忆：{"tags": "对话", "confirm": true}
"""
        # 定义参数
        self.parameters = [
            ToolParameter(
                name="keywords",
                param_type="string",
                description="要删除的记忆中包含的关键词",
                required=False
            ),
            ToolParameter(
                name="time_range",
                param_type="string",
                description="时间范围（如：5分钟前、1小时前、昨天）",
                required=False
            ),
            ToolParameter(
                name="tags",
                param_type="string",
                description="记忆标签（可选）",
                required=False
            ),
            ToolParameter(
                name="confirm",
                param_type="boolean",
                description="是否确认删除（true表示确认）",
                required=False,
                default=False
            )
        ]

    def _parse_time_range(self, time_str: str) -> Optional[datetime]:
        """解析时间范围字符串，返回起始时间"""
        now = datetime.now()
        time_str = time_str.lower().strip()

        # 处理"N分钟前"、"N小时前"、"N天前"
        if "分钟前" in time_str:
            try:
                minutes = int(time_str.replace("分钟前", "").strip())
                return now - timedelta(minutes=minutes)
            except ValueError:
                pass

        if "小时前" in time_str:
            try:
                hours = int(time_str.replace("小时前", "").strip())
                return now - timedelta(hours=hours)
            except ValueError:
                pass

        if "天前" in time_str:
            try:
                days = int(time_str.replace("天前", "").strip())
                return now - timedelta(days=days)
            except ValueError:
                pass

        # 处理"昨天"、"今天"
        if "昨天" in time_str:
            return now - timedelta(days=1)

        if "今天" in time_str:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 处理"最近"
        if "最近" in time_str:
            # 默认为最近1小时
            return now - timedelta(hours=1)

        return None

    async def execute(self, **kwargs) -> dict:
        """
        执行记忆删除

        Args:
            **kwargs: 包含 keywords, time_range, tags, confirm

        Returns:
            {"success": bool, "data": str}
        """
        keywords = kwargs.get("keywords")
        time_range = kwargs.get("time_range")
        tags = kwargs.get("tags")
        confirm = kwargs.get("confirm", False)

        try:
            # 构建查询条件
            conditions = []

            # 关键词过滤
            if keywords:
                keyword_list = [k.strip() for k in keywords.split(",")]
                keyword_conditions = [
                    Memory.content.contains(kw)
                    for kw in keyword_list
                ]
                conditions.append(or_(*keyword_conditions))

            # 时间范围过滤
            if time_range:
                start_time = self._parse_time_range(time_range)
                if start_time:
                    conditions.append(Memory.created_at >= start_time)
                else:
                    return {
                        "success": False,
                        "data": f"无法解析时间范围：{time_range}"
                    }

            # 标签过滤
            if tags:
                tag_list = [t.strip() for t in tags.split(",")]
                tag_conditions = [
                    Memory.tag.contains(tag_item) for tag_item in tag_list
                ]
                conditions.append(or_(*tag_conditions))

            # 如果没有任何条件，返回错误
            if not conditions:
                return {
                    "success": False,
                    "data": "请指定删除条件（关键词、时间范围或标签）"
                }

            # 查询符合条件的记忆
            query = self.db.query(Memory)
            if conditions:
                query = query.filter(and_(*conditions))

            memories = query.all()

            if not memories:
                return {
                    "success": True,
                    "data": "没有找到符合条件的记忆"
                }

            # 如果没有确认，只返回预览
            if not confirm:
                preview = f"找到 {len(memories)} 条符合条件的记忆：\n"
                for i, mem in enumerate(memories[:5], 1):
                    content = str(mem.content)[:50] + "..." if len(
                        str(mem.content)
                    ) > 50 else str(mem.content)
                    time_str = mem.created_at.strftime('%Y-%m-%d %H:%M')
                    preview += f"{i}. [{time_str}] {content}\n"

                if len(memories) > 5:
                    preview += f"...还有 {len(memories) - 5} 条记忆\n"

                preview += (
                    "\n如果确认删除，请再次调用并设置 confirm=true"
                )
                return {"success": True, "data": preview}

            # 确认后删除
            deleted_count = len(memories)
            for memory in memories:
                self.db.delete(memory)

            self.db.commit()

            logger.info(
                f"已删除 {deleted_count} 条记忆 "
                f"(keywords={keywords}, time_range={time_range}, "
                f"tags={tags})"
            )

            return {
                "success": True,
                "data": f"✅ 已成功删除 {deleted_count} 条记忆"
            }

        except Exception as e:
            logger.error(f"删除记忆失败: {e}", exc_info=True)
            self.db.rollback()
            return {
                "success": False,
                "data": f"删除记忆时发生错误：{str(e)}"
            }


def get_tool():
    """获取工具实例"""
    return DeleteMemoryTool()
