import os
from functools import lru_cache
from agent import get_xiaole_agent
from .cache import HomeCache
from .gateways.action_readiness import ActionReadinessGateway
from .gateways.lezhi import LezhiHomeGateway
from .service import HomeService

class RecentConversations:
    def recent(self,user): return get_xiaole_agent().conversation.get_recent_sessions(user,5)

@lru_cache(maxsize=1)
def build_home_service():
    return HomeService(LezhiHomeGateway(os.getenv("LEZHI_MEMORY_URL","http://127.0.0.1:8765"),os.getenv("LEZHI_MEMORY_TOKEN",""),float(os.getenv("HOME_LEZHI_TIMEOUT_SECONDS","2.5"))),ActionReadinessGateway(os.getenv("XIAOKE_ACTION_URL",""),os.getenv("XIAOKE_API_TOKEN",""),float(os.getenv("HOME_ACTION_TIMEOUT_SECONDS","1.5")),os.getenv("XIAOKE_HEALTH_PATH","/health")),RecentConversations(),HomeCache(),float(os.getenv("HOME_TOTAL_BUDGET_SECONDS","3")))
