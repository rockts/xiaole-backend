from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from datetime import datetime
from typing import Any

from .mappers import map_no_notification, map_profile, map_recommendation

QUICK_QUESTIONS = ["最近有什么值得我关注？", "为什么最近没通知我？", "最近有哪些比赛我可以参加？", "最近有什么截止日期？", "乐知最近收了什么？", "给我手机发一条通知"]


class HomeService:
    def __init__(self, lezhi, action, conversations, cache, budget: float = 3.0):
        self.lezhi, self.action, self.conversations, self.cache, self.budget = lezhi, action, conversations, cache, budget

    def get(self, user: str) -> dict[str, Any]:
        fresh = self.cache.get_fresh(user)
        if fresh:
            return fresh
        generated = datetime.now().astimezone().isoformat()
        calls = {"intelligence":self.lezhi.intelligence,"knowledge":self.lezhi.knowledge,"profile":self.lezhi.profile,"profile_status":self.lezhi.profile_status,"action":self.action.check,"conversations":lambda:self.conversations.recent(user)}
        results, failures = {}, []
        executor = ThreadPoolExecutor(max_workers=6)
        futures = {name: executor.submit(call) for name, call in calls.items()}
        try:
            done, _ = wait(futures.values(), timeout=self.budget)
            for name, future in futures.items():
                if future not in done:
                    future.cancel(); failures.append(name); continue
                try: results[name] = future.result()
                except Exception: failures.append(name)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        if not results.get("intelligence"):
            stale = self.cache.get_stale(user)
            if stale:
                value, age = stale
                value["cache"]={"status":"stale","generated_at":value["generated_at"],"age_seconds":age}
                value["systems"]["memory"]={"status":"degraded","label":"乐知 Memory","message":"数据更新暂时延迟，当前显示最近一次结果。"}
                value["degradations"]=[*value.get("degradations",[]),{"dependency":"lezhi","code":"stale","message":"数据更新暂时延迟，当前显示最近一次结果。"}]
                return value
        value = self._build(generated, results, failures)
        if results.get("intelligence"): self.cache.put(user, value)
        return value

    def _build(self, generated, results, failures):
        intel, knowledge = results.get("intelligence"), results.get("knowledge")
        degradations=[]
        if intel:
            raw=intel.get("today") if isinstance(intel.get("today"),dict) else {}; healthy=int(raw.get("sources_healthy") or 0); unhealthy=int(raw.get("sources_unhealthy") or 0); relevant=int(raw.get("relevant") or 0)
            today={"status":"available","date":generated[:10],"summary":f"今天乐知已完成扫描，{healthy} 个来源正常、{unhealthy} 个异常；"+("目前没有需要你立即处理的新事项。" if relevant==0 else f"有 {relevant} 项值得关注。"),"last_scan_at":raw.get("last_scan") or None,"next_scan_at":raw.get("next_scan") or None,"sources":{"healthy":healthy,"unhealthy":unhealthy},"new_discovered":int(raw.get("new_discovered") or 0),"relevant":relevant,"notified":int(raw.get("notified") or 0)}
            items=[map_recommendation(x) for x in intel.get("recommended_items") or [] if isinstance(x,dict) and str(x.get("title") or "").strip()][:5]
            recommendations={"status":"available","items":items,"empty_message":"目前没有需要优先处理的事项。"}; no_notice=map_no_notification(intel)
        else:
            today={"status":"unavailable","date":generated[:10],"summary":"乐知暂时不可用，知识与情报状态无法更新。","last_scan_at":None,"next_scan_at":None,"sources":{"healthy":0,"unhealthy":0},"new_discovered":0,"relevant":0,"notified":0}; recommendations={"status":"unavailable","items":[],"empty_message":"目前无法更新值得关注的事项。"}; no_notice={"status":"unavailable","period_days":7,"summary":"暂时无法更新最近通知原因。","true_new":0,"categories":[]}; degradations.append({"dependency":"lezhi","code":"unavailable","message":"乐知暂时不可用，知识与情报状态无法更新。"})
        memory="unavailable" if not intel and not knowledge else "degraded" if not intel or not knowledge else self._memory_status(intel)
        action=results.get("action"); action_status=getattr(action,"status","unavailable"); action_message=getattr(action,"message","行动服务状态暂时无法确认。")
        if action_status!="healthy": degradations.append({"dependency":"xiaoke","code":"unavailable","message":action_message})
        profile=map_profile(results["profile"],results["profile_status"]) if results.get("profile") is not None and results.get("profile_status") is not None else {"status":"unavailable","needs_confirmation_count":0,"message":"","fields":[]}
        conversations=[{"session_id":str(x["session_id"]),"title":str(x.get("title") or "未命名对话"),"updated_at":str(x.get("updated_at") or "")} for x in results.get("conversations") or [] if isinstance(x,dict) and x.get("session_id")]
        if "conversations" in failures: degradations.append({"dependency":"conversations","code":"unavailable","message":"最近会话暂时无法加载。"})
        messages={"healthy":"知识与情报服务正常。","degraded":"知识与情报服务部分数据暂不可用。","unavailable":"知识与情报服务暂时不可用。"}
        return {"schema_version":1,"generated_at":generated,"cache":{"status":"fresh","generated_at":generated,"age_seconds":0},"today":today,"recommendations":recommendations,"no_notification_summary":no_notice,"systems":{"brain":{"status":"healthy","label":"小乐 Brain","message":"小乐服务正常。"},"memory":{"status":memory,"label":"乐知 Memory","message":messages[memory]},"action":{"status":action_status,"label":"小可 Action","message":action_message}},"profile_status":profile,"recent_conversations":conversations,"quick_questions":deepcopy(QUICK_QUESTIONS),"degradations":degradations}

    @staticmethod
    def _memory_status(intel):
        health=intel.get("system_health") if isinstance(intel.get("system_health"),dict) else {}
        return "degraded" if any(health.get(k) in {"degraded","failed","unavailable"} for k in ("memory_service","sources","intelligence_scheduler")) else "healthy"
