"""
定时任务调度器 - v0.5.0
功能：
1. 定期检查提醒触发条件
2. 后台任务队列
3. 任务执行历史
"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.reminder_manager import get_reminder_manager
from backend.proactive_chat import get_proactive_chat
from backend.memory import MemoryManager
from pathlib import Path
from backend.conflict_detector import ConflictDetector

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
    """
    提醒调度器
    功能：
    1. 定期检查时间提醒（每分钟）
    2. 定期检查行为提醒（每5分钟）
    3. 支持手动触发检查
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.reminder_manager = get_reminder_manager()
        self.proactive_chat = get_proactive_chat()
        self.memory_manager = MemoryManager()
        self.is_running = False

    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # 任务1: 每分钟检查时间提醒
        self.scheduler.add_job(
            self.check_time_reminders,
            trigger=IntervalTrigger(minutes=1),
            id='check_time_reminders',
            name='检查时间提醒',
            replace_existing=True
        )

        # 任务2: 每5分钟检查行为提醒
        self.scheduler.add_job(
            self.check_behavior_reminders,
            trigger=IntervalTrigger(minutes=5),
            id='check_behavior_reminders',
            name='检查行为提醒',
            replace_existing=True
        )

        # 任务3: 每天凌晨3点清理过期提醒
        self.scheduler.add_job(
            self.cleanup_expired_reminders,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_expired',
            name='清理过期提醒',
            replace_existing=True
        )

        # 任务4: 每小时检查是否需要主动对话
        self.scheduler.add_job(
            self.check_proactive_chat,
            trigger=IntervalTrigger(hours=1),
            id='check_proactive_chat',
            name='检查主动对话',
            replace_existing=True
        )

        # 任务5: 每天凌晨4点清理旧记忆
        self.scheduler.add_job(
            self.cleanup_old_memories,
            trigger=CronTrigger(hour=4, minute=0),
            id='cleanup_old_memories',
            name='清理旧记忆',
            replace_existing=True
        )

        # 任务6: 每天凌晨2点运行记忆冲突检测并写入日志
        self.scheduler.add_job(
            self.run_conflict_detector_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='conflict_detector_daily',
            name='记忆冲突检测',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Reminder scheduler started")

    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Reminder scheduler stopped")

    def check_time_reminders(self):
        """检查所有用户的时间提醒"""
        print("==== FUNCTION ENTERED ====", flush=True)
        logger.info("==== CHECK_TIME_REMINDERS STARTED ====")
        try:
            print("==== TRY BLOCK ENTERED ====", flush=True)
            logger.info("Checking time reminders...")
            print("==== AFTER FIRST LOG ====", flush=True)
            logger.info("Step 1: Importing database functions")

            # 获取所有有提醒的用户
            from reminder_manager import get_db_connection
            from psycopg2.extras import RealDictCursor
            print("==== IMPORTS DONE ====", flush=True)

            logger.info("Step 2: Getting database connection")
            conn = get_db_connection()
            try:
                logger.info("Step 3: Querying users")
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT DISTINCT user_id FROM reminders WHERE enabled = true"
                    )
                    users = [row['user_id'] for row in cur.fetchall()]
                    logger.info(f"Found users: {users}")
            except Exception as db_error:
                logger.error(f"Database query failed: {db_error}")
                raise
            finally:
                logger.info("Step 4: Closing connection")
                conn.close()

            if not users:
                logger.warning("No active users with reminders found!")
                return

            logger.info(f"Step 5: Checking reminders for {len(users)} users")
            total_triggered = 0
            for user_id in users:
                logger.info(f"Checking user: {user_id}")
                triggered = self.reminder_manager.check_time_reminders(
                    user_id
                )
                logger.info(f"User {user_id} has {len(triggered)} triggered")

                for reminder in triggered:
                    success = self.reminder_manager.check_and_notify_reminder(
                        reminder['reminder_id']
                    )
                    if success:
                        total_triggered += 1
                        logger.info(
                            f"Triggered time reminder: "
                            f"{reminder.get('title', 'Untitled')} "
                            f"for user {user_id}"
                        )

            if total_triggered > 0:
                logger.info(
                    f"Time reminder check complete: "
                    f"{total_triggered} reminders triggered"
                )
            else:
                logger.info("No reminders triggered this cycle")

        except Exception as e:
            logger.error(f"Error checking time reminders: {e}", exc_info=True)

    def check_behavior_reminders(self):
        """检查所有用户的行为提醒"""
        try:
            logger.info("Checking behavior reminders...")

            # 获取所有有提醒的用户
            from reminder_manager import get_db_connection
            from psycopg2.extras import RealDictCursor

            conn = get_db_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT DISTINCT user_id FROM reminders WHERE enabled = true"
                    )
                    users = [row['user_id'] for row in cur.fetchall()]
            finally:
                conn.close()

            if not users:
                return

            total_triggered = 0
            for user_id in users:
                triggered = self.reminder_manager.check_behavior_reminders(
                    user_id
                )

                for reminder in triggered:
                    success = self.reminder_manager.check_and_notify_reminder(
                        reminder['reminder_id']
                    )
                    if success:
                        total_triggered += 1
                        logger.info(
                            f"Triggered behavior reminder: "
                            f"{reminder.get('title', 'Untitled')} "
                            f"for user {user_id}"
                        )

            if total_triggered > 0:
                logger.info(
                    f"Behavior reminder check complete: "
                    f"{total_triggered} reminders triggered"
                )

        except Exception as e:
            logger.error(f"Error checking behavior reminders: {e}")

    def cleanup_expired_reminders(self):
        """清理过期的非重复提醒"""
        try:
            logger.info("Cleaning up expired reminders...")

            # TODO: 实现清理逻辑
            # 删除已触发且非重复的提醒（保留最近30天）

            logger.info("Cleanup complete")

        except Exception as e:
            logger.error(f"Error cleaning up reminders: {e}")

    def check_proactive_chat(self):
        """检查是否需要发起主动对话"""
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

                    # 通过WebSocket推送主动对话
                    if self.reminder_manager.websocket_callback:
                        # websocket_callback 是一个 async 函数,但我们不能在同步函数中 await
                        # 使用 asyncio.create_task 在后台执行
                        asyncio.create_task(
                            self.reminder_manager.websocket_callback({
                                "type": "proactive_chat",
                                "user_id": user_id,
                                "reason": result["reason"],
                                "message": result["message"],
                                "priority": result["priority"],
                                "metadata": result.get("metadata", {})
                            })
                        )

                        # 标记已发起
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


# 全局单例
_scheduler = None


def get_scheduler() -> ReminderScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReminderScheduler()
    return _scheduler
