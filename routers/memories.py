from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, List
from backend.dependencies import get_xiaole_agent, get_conflict_detector
from backend.agent import XiaoLeAgent
from backend.conflict_detector import ConflictDetector
from backend.memory import MemoryManager
from backend.logger import logger

router = APIRouter(
    prefix="",
    tags=["memory"]
)


def get_agent():
    return get_xiaole_agent()


def get_detector():
    return get_conflict_detector()


@router.get("/memory")
def memory(
    tag: str = "general",
    limit: int = 10,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """获取指定标签的记忆"""
    return {"memory": agent.memory.recall(tag, limit=limit)}


@router.get("/memory/recent")
def memory_recent(
    hours: int = 24,
    tag: Optional[str] = None,
    limit: int = 10,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """获取最近N小时的记忆"""
    return {"memory": agent.memory.recall_recent(hours, tag, limit)}


@router.get("/memory/search")
def memory_search(
    keywords: str,
    tag: Optional[str] = None,
    limit: int = 10,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """通过关键词搜索记忆"""
    kw_list = [kw.strip() for kw in keywords.split(',')]
    memories = agent.memory.recall_by_keywords(kw_list, tag, limit)
    return {"memories": memories}


@router.get("/memory/semantic")
def memory_semantic_search(
    query: str,
    tag: Optional[str] = None,
    limit: int = 10,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """语义搜索记忆"""
    memories = agent.memory.semantic_recall(query, tag, limit, min_score=0.1)
    return {"memories": memories}


@router.get("/memory/stats")
def memory_stats(agent: XiaoLeAgent = Depends(get_agent)):
    """获取记忆统计信息"""
    return agent.memory.get_stats()


@router.put("/memory/{memory_id}")
async def update_memory(memory_id: int, request: dict):
    """更新记忆内容"""
    try:
        memory_manager = MemoryManager()
        from db_setup import Memory

        memory = memory_manager.session.query(Memory).filter(
            Memory.id == memory_id
        ).first()

        if not memory:
            raise HTTPException(status_code=404, detail="记忆不存在")

        content = request.get("content")
        tag = request.get("tag")

        if content:
            memory.content = content
        if tag:
            memory.tag = tag

        memory_manager.session.commit()

        return {
            "success": True,
            "message": "记忆已更新"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int):
    """删除记忆"""
    try:
        memory_manager = MemoryManager()
        from db_setup import Memory

        memory = memory_manager.session.query(Memory).filter(
            Memory.id == memory_id
        ).first()

        if not memory:
            raise HTTPException(status_code=404, detail="记忆不存在")

        memory_manager.session.delete(memory)
        memory_manager.session.commit()

        return {
            "success": True,
            "message": "记忆已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除记忆失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/conflicts")
def check_memory_conflicts(
    tag: str = "facts",
    limit: int = 100,
    detector: ConflictDetector = Depends(get_detector)
):
    """检测记忆冲突"""
    conflicts = detector.detect_conflicts(tag, limit)
    return {
        "has_conflicts": len(conflicts) > 0,
        "total": len(conflicts),
        "conflicts": conflicts
    }


@router.get("/memory/conflicts/summary")
def get_conflict_summary(
    detector: ConflictDetector = Depends(get_detector)
):
    """获取冲突摘要"""
    return detector.get_conflict_summary()


@router.get("/memory/conflicts/report")
def get_conflict_report(
    detector: ConflictDetector = Depends(get_detector)
):
    """获取可读的冲突报告"""
    report = detector.generate_conflict_report()
    return {"report": report}
