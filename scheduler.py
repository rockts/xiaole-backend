"""
共享后台任务调度器。
"""
import asyncio
import logging
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from modules.proactive_chat import get_proactive_chat
from memory import MemoryManager
from pathlib import Path
from modules.conflict_detector import ConflictDetector
from llm_gateway import GovernanceUnavailable, get_llm_gateway

logger = logging.getLogger(__name__)

# 确保 logger 配置正确
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ReminderScheduler:
    """保留主动对话和记忆维护的共享后台调度器。"""
    _start_lock = threading.Lock()

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.proactive_chat = get_proactive_chat()
        self.memory_manager = MemoryManager()
        self.llm_gateway = get_llm_gateway()
        self.websocket_broadcast = None
        self.event_loop = None
        self.is_running = False

    def configure_websocket(self, broadcast, event_loop):
        """配置非提醒后台任务使用的通用 WebSocket 通道。"""
        self.websocket_broadcast = broadcast
        self.event_loop = event_loop

    def start(self):
        """启动调度器"""
        with self._start_lock:
            if self.is_running:
                logger.warning("Scheduler is already running")
                return
            self.is_running = True

        # 每小时检查是否需要主动对话
        self.scheduler.add_job(
            self.check_proactive_chat,
            trigger=IntervalTrigger(hours=1),
            id='check_proactive_chat',
            name='检查主动对话',
            replace_existing=True
        )

        # 每天凌晨4点清理旧记忆
        self.scheduler.add_job(
            self.cleanup_old_memories,
            trigger=CronTrigger(hour=4, minute=0),
            id='cleanup_old_memories',
            name='清理旧记忆',
            replace_existing=True
        )

        # 每天凌晨2点运行记忆冲突检测并写入日志
        self.scheduler.add_job(
            self.run_conflict_detector_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='conflict_detector_daily',
            name='记忆冲突检测',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Background scheduler started")

    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Background scheduler stopped")

    def check_proactive_chat(self):
        """检查是否需要发起主动对话"""
        if not self._acquire_job_lease("check_proactive_chat", "%Y%m%d%H", 3900):
            return
        try:
            logger.info("Checking proactive chat conditions...")

            # TODO: 获取所有活跃用户列表
            users = ["default_user"]

            for user_id in users:
                result = self.proactive_chat.should_initiate_chat(user_id)

                if result["should_chat"]:
                    logger.info(
                        f"Proactive chat triggered for {user_id}: "
                        f"{result['reason']} (priority: {result['priority']})"
                    )

                    if self.websocket_broadcast and self.event_loop:
                        asyncio.run_coroutine_threadsafe(
                            self.websocket_broadcast({
                                "type": "proactive_chat",
                                "user_id": user_id,
                                "reason": result["reason"],
                                "message": result["message"],
                                "priority": result["priority"],
                                "metadata": result.get("metadata", {})
                            }),
                            self.event_loop,
                        )
                        self.proactive_chat.mark_chat_initiated(
                            user_id,
                            result["reason"],
                            result["message"]
                        )
                        logger.info(f"Proactive chat sent to {user_id}")

        except Exception as e:
            logger.error(f"Error checking proactive chat: {e}")

    def get_jobs(self):
        """获取所有任务信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat()
                if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    def get_status(self):
        """获取调度器状态"""
        return {
            "running": self.is_running,
            "total_jobs": len(self.scheduler.get_jobs()),
            "jobs": self.get_jobs()
        }

    def cleanup_old_memories(self):
        """清理旧记忆 - 每天凌晨4点执行"""
        if not self._acquire_job_lease("cleanup_old_memories", "%Y%m%d", 7200):
            return
        try:
            logger.info("Starting memory cleanup...")

            # 清理30天前的conversation记忆 (v0.9.2: 延长至30天以改善跨对话记忆)
            count = self.memory_manager.cleanup_old_conversations(days=30)

            logger.info(
                f"Memory cleanup complete: "
                f"removed {count} old conversation memories"
            )

        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")

    def run_conflict_detector_job(self):
        """运行记忆冲突检测 - 每天凌晨2点执行，输出到日志文件"""
        if not self._acquire_job_lease("conflict_detector_daily", "%Y%m%d", 7200):
            return
        try:
            logger.info("Running conflict detector job...")
            detector = ConflictDetector()
            report = detector.generate_conflict_report()

            # 日志文件路径：项目根目录 logs/conflict_report.log
            backend_dir = Path(__file__).resolve().parent
            root_dir = backend_dir.parent
            logs_dir = root_dir / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / 'conflict_report.log'

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"[{timestamp}] 记忆冲突检测报告\n")
                f.write("-" * 80 + "\n")
                f.write(report.strip() + "\n")
                f.write("=" * 80 + "\n")

            logger.info(
                "Conflict detector job finished; report written to "
                "logs/conflict_report.log"
            )
        except Exception as e:
            logger.error(f"Error running conflict detector job: {e}")

    def _acquire_job_lease(
        self, job_id: str, bucket_format: str, ttl_seconds: int
    ) -> bool:
        bucket = datetime.now().strftime(bucket_format)
        try:
            acquired = self.llm_gateway.acquire_execution_lease(
                f"scheduler:{job_id}:{bucket}", ttl_seconds=ttl_seconds
            )
        except GovernanceUnavailable:
            logger.error(
                "scheduler_governance_unavailable job=%s action=fail_closed",
                job_id,
            )
            return False
        if not acquired:
            logger.info("scheduler_duplicate_skipped job=%s bucket=%s", job_id, bucket)
        return acquired


# 全局单例
_scheduler = None


def get_scheduler() -> ReminderScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReminderScheduler()
    return _scheduler
