"""
任务执行引擎
负责执行任务步骤、调用工具、处理用户确认等
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional

from backend.task_manager import TaskManager
from backend.tool_manager import ToolRegistry

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器"""

    def __init__(self, task_manager: TaskManager, tool_registry: ToolRegistry):
        """初始化任务执行器

        Args:
            task_manager: 任务管理器实例
            tool_registry: 工具注册器实例
        """
        self.task_manager = task_manager
        self.tool_registry = tool_registry

    def execute_task(
        self,
        task_id: int,
        user_id: str,
        session_id: str,
        user_confirm_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """执行任务

        Args:
            task_id: 任务ID
            user_id: 用户ID
            session_id: 会话ID
            user_confirm_callback: 用户确认回调函数,接收(step_info)返回bool

        Returns:
            执行结果
        """
        try:
            # 获取任务信息
            task = self.task_manager.get_task(task_id)
            if not task:
                return {
                    'success': False,
                    'error': f'任务不存在: {task_id}'
                }

            # 检查任务状态
            if task['status'] in ['completed', 'failed', 'cancelled']:
                return {
                    'success': False,
                    'error': f'任务状态无效: {task["status"]}'
                }

            # 更新任务状态为执行中
            self.task_manager.update_task_status(
                task_id=task_id,
                status='in_progress'
            )

            # 获取任务步骤
            steps = self.task_manager.get_task_steps(task_id)
            if not steps:
                return {
                    'success': False,
                    'error': '任务没有步骤'
                }

            # 执行步骤
            total_steps = len(steps)
            completed_steps = 0
            failed_steps = 0
            results = []

            for step in steps:
                # 跳过已完成或失败的步骤
                if step['status'] in ['completed', 'failed']:
                    if step['status'] == 'completed':
                        completed_steps += 1
                    else:
                        failed_steps += 1
                    continue

                # 执行步骤
                step_result = self._execute_step(
                    step=step,
                    user_confirm_callback=user_confirm_callback,
                    task_id=task_id,
                    user_id=user_id,
                    session_id=session_id
                )

                results.append({
                    'step_id': step['id'],
                    'step_order': step['step_num'],
                    'title': step['description'],
                    'result': step_result
                })

                # 检查是否需要等待用户确认
                if step_result.get('status') == 'waiting':
                    self.task_manager.update_step_status(
                        step_id=step['id'],
                        status='waiting',
                        result=json.dumps(step_result, ensure_ascii=False)
                    )
                    # 停止执行循环
                    break

                # 更新步骤状态
                if step_result['success']:
                    self.task_manager.update_step_status(
                        step_id=step['id'],
                        status='completed',
                        result=json.dumps(step_result, ensure_ascii=False)
                    )
                    completed_steps += 1
                else:
                    self.task_manager.update_step_status(
                        step_id=step['id'],
                        status='failed',
                        error=step_result.get('error', '未知错误')
                    )
                    failed_steps += 1

                    # 如果步骤失败,判断是否继续
                    if not step.get('continue_on_error', False):
                        logger.warning(f"步骤失败,停止执行: {step['description']}")
                        break

            # 更新任务状态
            if failed_steps > 0 and completed_steps == 0:
                # 全部失败
                final_status = 'failed'
            elif completed_steps == total_steps:
                # 全部完成
                final_status = 'completed'
            elif failed_steps > 0:
                # 部分失败
                final_status = 'failed'
            else:
                # 仍在执行中(可能有等待步骤)
                final_status = 'waiting'

            self.task_manager.update_task_status(
                task_id=task_id,
                status=final_status
            )

            return {
                'success': True,
                'task_id': task_id,
                'status': final_status,
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'failed_steps': failed_steps,
                'results': results
            }

        except Exception as e:
            logger.error(f"执行任务失败: {e}", exc_info=True)
            # 更新任务状态为失败
            try:
                self.task_manager.update_task_status(
                    task_id=task_id,
                    status='failed'
                )
            except Exception:
                pass

            return {
                'success': False,
                'error': str(e)
            }

    def _execute_step(
        self,
        step: Dict[str, Any],
        user_confirm_callback: Optional[callable] = None,
        task_id: Optional[int] = None,
        user_id: str = "default_user",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行单个步骤

        Args:
            step: 步骤信息
            user_confirm_callback: 用户确认回调
            task_id: 任务ID
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            执行结果
        """
        action_type = step['action_type']
        action_params = step.get('action_params', {})

        try:
            if action_type == 'tool_call':
                # 调用工具
                return self._execute_tool_call(
                    params=action_params,
                    task_id=task_id,
                    user_id=user_id,
                    session_id=session_id
                )

            elif action_type == 'user_confirm':
                # 用户确认
                return self._execute_user_confirm(step, user_confirm_callback)

            elif action_type == 'wait':
                # 等待
                return self._execute_wait(action_params)

            elif action_type == 'info':
                # 信息展示
                return {
                    'success': True,
                    'message': step.get('description', ''),
                    'action_type': 'info'
                }

            else:
                return {
                    'success': False,
                    'error': f'未知的步骤类型: {action_type}'
                }

        except Exception as e:
            logger.error(f"执行步骤失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _execute_tool_call(
        self,
        params: Dict[str, Any],
        task_id: Optional[int] = None,
        user_id: str = "default_user",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行工具调用

        Args:
            params: 工具参数,格式: {"tool_name": "xxx", "params": {...}}
            task_id: 任务ID
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            执行结果
        """
        try:
            tool_name = params.get('tool_name')
            tool_params = params.get('params', {})

            if not tool_name:
                return {
                    'success': False,
                    'error': '缺少工具名称'
                }

            # 调用工具
            logger.info(f"调用工具: {tool_name}")
            # 使用 asyncio.run 执行异步工具方法
            result = asyncio.run(self.tool_registry.execute(
                tool_name=tool_name,
                params=tool_params,
                user_id=user_id,
                session_id=session_id,
                task_id=task_id
            ))

            return {
                'success': True,
                'tool_name': tool_name,
                'result': result,
                'action_type': 'tool_call'
            }

        except Exception as e:
            logger.error(f"工具调用失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'工具调用失败: {str(e)}'
            }

    def _execute_user_confirm(
        self,
        step: Dict[str, Any],
        callback: Optional[callable]
    ) -> Dict[str, Any]:
        """执行用户确认

        Args:
            step: 步骤信息
            callback: 确认回调函数

        Returns:
            执行结果
        """
        if not callback:
            # 没有回调函数, 暂停任务等待用户确认
            logger.info("用户确认步骤没有回调函数, 暂停任务等待用户确认")
            return {
                'success': True,
                'confirmed': False,
                'action_type': 'user_confirm',
                'status': 'waiting',
                'message': step.get('description', '需要用户确认')
            }

        try:
            # 调用回调函数获取用户确认
            confirmed = callback(step)

            return {
                'success': True,
                'confirmed': confirmed,
                'action_type': 'user_confirm'
            }

        except Exception as e:
            logger.error(f"用户确认失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'用户确认失败: {str(e)}'
            }

    def _execute_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行等待

        Args:
            params: 等待参数,格式: {"duration": 秒数, "reason": "原因"}

        Returns:
            执行结果
        """
        duration = params.get('duration', 0)
        reason = params.get('reason', '')

        logger.info(f"等待 {duration} 秒: {reason}")

        # 注意: 实际等待应该在异步任务中处理
        # 这里只是记录等待信息
        return {
            'success': True,
            'duration': duration,
            'reason': reason,
            'action_type': 'wait',
            'message': f'需要等待 {duration} 秒: {reason}'
        }

    def resume_task(
        self,
        task_id: int,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """恢复执行任务(从上次中断处继续)

        Args:
            task_id: 任务ID
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            执行结果
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return {
                'success': False,
                'error': f'任务不存在: {task_id}'
            }

        if task['status'] != 'waiting':
            return {
                'success': False,
                'error': f'任务状态不是waiting,无法恢复: {task["status"]}'
            }

        # 调用execute_task继续执行
        return self.execute_task(
            task_id=task_id,
            user_id=user_id,
            session_id=session_id
        )

    def cancel_task(self, task_id: int) -> Dict[str, Any]:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            操作结果
        """
        try:
            task = self.task_manager.get_task(task_id)
            if not task:
                return {
                    'success': False,
                    'error': f'任务不存在: {task_id}'
                }

            if task['status'] in ['completed', 'failed', 'cancelled']:
                return {
                    'success': False,
                    'error': f'任务已结束,无法取消: {task["status"]}'
                }

            # 更新状态为已取消
            self.task_manager.update_task_status(
                task_id=task_id,
                status='cancelled'
            )

            return {
                'success': True,
                'message': '任务已取消'
            }

        except Exception as e:
            logger.error(f"取消任务失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
