"""
错误处理和重试机制
"""
import time
import logging
from functools import wraps
from typing import Callable, Any
import os

# 配置日志
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(
            log_dir, 'xiaole_ai.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('xiaole_ai')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器，支持指数退避

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"{func.__name__} 在第 {attempt + 1} 次尝试后成功")
                    return result

                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"等待 {delay:.1f} 秒后重试..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然失败: {str(e)}"
                        )

            # 所有重试都失败
            raise last_exception

        return wrapper
    return decorator


def log_execution(func: Callable) -> Callable:
    """记录函数执行的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger.info(f"开始执行: {func.__name__}")
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"执行完成: {func.__name__} (耗时: {elapsed:.2f}秒)")
            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"执行失败: {func.__name__} (耗时: {elapsed:.2f}秒) - {str(e)}"
            )
            raise

    return wrapper


class APIError(Exception):
    """API调用错误基类"""
    pass


class APITimeoutError(APIError):
    """API超时错误"""
    pass


class APIRateLimitError(APIError):
    """API限流错误"""
    pass


class APIConnectionError(APIError):
    """API连接错误"""
    pass


def handle_api_errors(func: Callable) -> Callable:
    """处理API相关错误的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()

            if 'timeout' in error_msg or 'timed out' in error_msg:
                raise APITimeoutError(f"API调用超时: {str(e)}")
            elif 'rate limit' in error_msg or 'too many requests' in error_msg:
                raise APIRateLimitError(f"API限流: {str(e)}")
            elif 'connection' in error_msg or 'network' in error_msg:
                raise APIConnectionError(f"API连接失败: {str(e)}")
            else:
                raise APIError(f"API调用失败: {str(e)}")

    return wrapper
