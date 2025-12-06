from fastapi import APIRouter, Depends
from typing import Dict, Any, Optional
from dependencies import get_xiaole_agent
from agent import XiaoLeAgent

router = APIRouter(
    prefix="/tools",
    tags=["tools"]
)


def get_agent():
    return get_xiaole_agent()


@router.get("/list")
def list_tools(
    category: Optional[str] = None,
    enabled_only: bool = True,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """列出所有可用工具"""
    tools = agent.tool_registry.list_tools(category, enabled_only)
    return {
        "total": len(tools),
        "tools": tools
    }


@router.post("/execute")
async def execute_tool(
    tool_name: str,
    params: dict,
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """执行指定工具"""
    result = await agent.tool_registry.execute(
        tool_name=tool_name,
        params=params,
        user_id=user_id,
        session_id=session_id
    )
    return result


@router.get("/history")
def get_tool_history(
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    limit: int = 20
):
    """获取工具执行历史"""
    from db_setup import SessionLocal, ToolExecution

    db = SessionLocal()
    try:
        query = db.query(ToolExecution).filter(
            ToolExecution.user_id == user_id
        )

        if session_id:
            query = query.filter(ToolExecution.session_id == session_id)

        executions = query.order_by(
            ToolExecution.executed_at.desc()
        ).limit(limit).all()

        return {
            "total": len(executions),
            "history": [
                {
                    "execution_id": e.execution_id,
                    "tool_name": e.tool_name,
                    "success": e.success,
                    "execution_time": e.execution_time,
                    "executed_at": e.executed_at.isoformat(),
                    "error_message": e.error_message
                }
                for e in executions
            ]
        }
    finally:
        db.close()
