from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reminder_manager import get_db_connection

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"]
)


class FeedbackRequest(BaseModel):
    session_id: str
    message_content: str
    feedback_type: str  # 'good' or 'bad'
    timestamp: str
    user_id: str = "default_user"


@router.post("")
async def submit_feedback(feedback: FeedbackRequest):
    """
    提交用户反馈
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO message_feedback 
            (session_id, user_id, message_content, feedback_type, created_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING feedback_id
        """, (
            feedback.session_id,
            feedback.user_id,
            feedback.message_content,
            feedback.feedback_type,
            feedback.timestamp
        ))

        feedback_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "feedback_id": feedback_id,
            "message": "反馈已记录，感谢您的反馈！"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_feedback_stats():
    """
    获取反馈统计数据
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                feedback_type,
                COUNT(*) as count,
                DATE(created_at) as date
            FROM message_feedback
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY feedback_type, DATE(created_at)
            ORDER BY date DESC
        """)

        stats = []
        for row in cursor.fetchall():
            stats.append({
                "feedback_type": row[0],
                "count": row[1],
                "date": str(row[2])
            })

        cursor.execute("""
            SELECT 
                SUM(CASE WHEN feedback_type = 'good' THEN 1 ELSE 0 END) as good_count,
                SUM(CASE WHEN feedback_type = 'bad' THEN 1 ELSE 0 END) as bad_count,
                COUNT(*) as total_count
            FROM message_feedback
        """)

        row = cursor.fetchone()
        summary = {
            "good_count": row[0] or 0,
            "bad_count": row[1] or 0,
            "total_count": row[2] or 0,
            "satisfaction_rate": round((row[0] or 0) / (row[2] or 1) * 100, 2) if row[2] else 0
        }

        cursor.close()
        conn.close()

        return {
            "success": True,
            "stats": stats,
            "summary": summary
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
