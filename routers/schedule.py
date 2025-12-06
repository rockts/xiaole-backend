from fastapi import APIRouter
from backend.memory import MemoryManager
from sqlalchemy import or_
from backend.db_setup import Memory
import re

router = APIRouter(
    prefix="/schedule",
    tags=["schedule"]
)


@router.get("")
async def get_schedule(user_id: str = "default_user"):
    """获取用户课程表"""
    try:
        memory_manager = MemoryManager()

        memories = memory_manager.session.query(Memory).filter(
            Memory.tag.like('image:%'),
            or_(
                Memory.content.like('%周一：晨读%'),
                Memory.content.like('%周一：第1节%'),
                Memory.content.like('%第1节-无课%')
            )
        ).order_by(Memory.created_at.desc()).limit(1).all()

        if not memories:
            memories = memory_manager.session.query(Memory).filter(
                Memory.tag == 'schedule'
            ).order_by(Memory.created_at.desc()).limit(1).all()

        if memories:
            content = memories[0].content
            schedule = {
                "periods": ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节'],
                "weekdays": ['周一', '周二', '周三', '周四', '周五'],
                "courses": {}
            }

            lines = content.split('\n')

            for line in lines:
                match = re.match(r'^(周[一二三四五])[:：]\s*(.*)', line)
                if match:
                    day = match.group(1)
                    course_info = match.group(2)
                    items = course_info.split(',')

                    for item in items:
                        item = item.strip()
                        if '第' in item and '节' in item:
                            period_match = re.search(r'第(\d+)节', item)
                            if period_match:
                                period_num = int(period_match.group(1))
                                course_match = re.search(r'-\s*(.+)', item)
                                if course_match:
                                    course_name = course_match.group(1).strip()
                                    if course_name and course_name != '无课':
                                        key = f"{period_num-1}_{day}"
                                        schedule["courses"][key] = course_name

            return {
                "success": True,
                "schedule": schedule
            }
        return {
            "success": True,
            "schedule": {
                "periods": ['第1节', '第2节', '第3节', '第4节', '第5节', '第6节', '第7节'],
                "weekdays": ['周一', '周二', '周三', '周四', '周五'],
                "courses": {}
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


@router.post("")
async def save_schedule(request: dict):
    """保存用户课程表"""
    try:
        schedule = request.get("schedule", {})

        if not schedule:
            return {
                "success": False,
                "error": "课程表数据为空"
            }

        memory_manager = MemoryManager()

        courses_by_day = {}
        for key, course in schedule.get("courses", {}).items():
            period_index, day = key.split('_')
            if day not in courses_by_day:
                courses_by_day[day] = {}
            courses_by_day[day][int(period_index)] = course

        lines = []
        for day in schedule.get("weekdays", []):
            if day in courses_by_day:
                courses = []
                for i in range(len(schedule.get("periods", []))):
                    course = courses_by_day[day].get(i, "无课")
                    courses.append(course)
                lines.append(f"{day}：{'-'.join(courses)}")

        content = "\n".join(lines)

        old_memories = memory_manager.session.query(Memory).filter(
            Memory.tag == 'schedule'
        ).all()

        for mem in old_memories:
            memory_manager.session.delete(mem)

        new_memory = Memory(
            content=f"用户课程表：\n{content}",
            tag="schedule"
        )
        memory_manager.session.add(new_memory)
        memory_manager.session.commit()

        return {
            "success": True,
            "message": "课程表保存成功"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }
