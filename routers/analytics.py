from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, Optional
from dependencies import get_xiaole_agent
from agent import XiaoLeAgent
from auth import get_current_user

router = APIRouter(
    prefix="",
    tags=["analytics"]
)


def get_agent():
    return get_xiaole_agent()


@router.get("/analytics/behavior")
def get_behavior_analytics(
    request: Request,
    days: int = 30,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取用户行为分析报告"""
    user_id = current_user
    report = agent.behavior_analyzer.generate_behavior_report(user_id, days)
    if not report or not report.get("conversation_stats"):
        raise HTTPException(status_code=404, detail="No data available")
    return report


@router.get("/analytics/activity")
def get_activity_pattern(
    request: Request,
    days: int = 30,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取用户活跃时间模式"""
    user_id = current_user
    pattern = agent.behavior_analyzer.get_user_activity_pattern(user_id, days)
    if not pattern:
        raise HTTPException(status_code=404, detail="No data available")
    return pattern


@router.get("/analytics/topics")
def get_topic_preferences(
    request: Request,
    days: int = 30,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取用户话题偏好"""
    user_id = current_user
    topics = agent.behavior_analyzer.get_topic_preferences(user_id, days)
    if not topics:
        raise HTTPException(status_code=404, detail="No data available")
    return topics


@router.get("/patterns/frequent")
def get_frequent_words(
    request: Request,
    limit: int = 20,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取用户高频词列表"""
    user_id = current_user
    words = agent.pattern_learner.get_frequent_words(user_id, limit)
    return {"user_id": user_id, "frequent_words": words}


@router.get("/patterns/common_questions")
def get_common_questions(
    request: Request,
    limit: int = 10,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取用户常见问题分类"""
    user_id = current_user
    questions = agent.pattern_learner.get_common_questions(user_id, limit)
    return {"user_id": user_id, "common_questions": questions}


@router.get("/patterns/insights")
def get_learning_insights(
    request: Request,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """获取模式学习统计洞察"""
    user_id = current_user
    insights = agent.pattern_learner.get_learning_insights(user_id)
    return insights


@router.post("/analytics/rebuild")
def rebuild_behavior_data(
    request: Request,
    agent: XiaoLeAgent = Depends(get_agent),
    current_user: str = Depends(get_current_user)
):
    """重建用户行为数据（扫描所有历史会话）"""
    from db_setup import SessionLocal, Conversation

    user_id = current_user
    db = SessionLocal()
    try:
        # 获取用户所有会话
        sessions = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).all()

        count = 0
        for sess in sessions:
            try:
                agent.behavior_analyzer.record_session_behavior(
                    user_id, sess.session_id
                )
                count += 1
            except Exception as e:
                print(f"Failed to record session {sess.session_id}: {e}")
                continue

        return {
            "success": True,
            "message": f"已重建 {count} 个会话的行为数据",
            "sessions_processed": count
        }
    finally:
        db.close()
