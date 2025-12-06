from agent import XiaoLeAgent
from conflict_detector import ConflictDetector
from proactive_qa import ProactiveQA
from reminder_manager import get_reminder_manager
from scheduler import get_scheduler
from task_manager import get_task_manager

# Global instances
_xiaole_agent = None
_conflict_detector = None
_proactive_qa = None


def get_xiaole_agent() -> XiaoLeAgent:
    global _xiaole_agent
    if _xiaole_agent is None:
        _xiaole_agent = XiaoLeAgent()
    return _xiaole_agent


def get_conflict_detector() -> ConflictDetector:
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = ConflictDetector()
    return _conflict_detector


def get_proactive_qa() -> ProactiveQA:
    global _proactive_qa
    if _proactive_qa is None:
        _proactive_qa = ProactiveQA()
    return _proactive_qa


# Re-export others for consistency
get_reminder_manager = get_reminder_manager
get_scheduler = get_scheduler
get_task_manager = get_task_manager
