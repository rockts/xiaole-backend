"""
系统操作工具

提供本地系统信息查询、文件操作、应用启动等功能
"""
import platform
import psutil
from typing import Dict, Any
from datetime import datetime
import logging
from backend.tool_manager import Tool, ToolParameter

logger = logging.getLogger(__name__)


class SystemInfoTool(Tool):
    """系统信息查询工具"""

    def __init__(self):
        super().__init__()
        self.name = "system_info"
        self.description = "查询系统信息（CPU、内存、磁盘、进程等）"
        self.category = "system"

        self.parameters = [
            ToolParameter(
                name="info_type",
                param_type="string",
                description=(
                    "信息类型: cpu(CPU信息), memory(内存信息), "
                    "disk(磁盘信息), all(全部信息)"
                ),
                required=False,
                default="all",
                enum=["cpu", "memory", "disk", "all"]
            )
        ]

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行系统信息查询"""
        info_type = kwargs.get('info_type', 'all')

        try:
            result_text = ""

            if info_type in ["cpu", "all"]:
                result_text += self._get_cpu_info()

            if info_type in ["memory", "all"]:
                result_text += "\n" + self._get_memory_info()

            if info_type in ["disk", "all"]:
                result_text += "\n" + self._get_disk_info()

            return {
                'success': True,
                'result': result_text.strip(),
                'error': None
            }

        except Exception as e:
            logger.error(f"系统信息查询异常: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"查询异常: {str(e)}",
                'result': None
            }

    def _get_cpu_info(self) -> str:
        """获取CPU信息"""
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()

        result = "🖥️ CPU信息\n"
        result += f"  处理器: {platform.processor()}\n"
        result += f"  物理核心: {cpu_count}个\n"
        result += f"  逻辑核心: {cpu_count_logical}个\n"
        result += f"  使用率: {cpu_percent}%\n"
        if cpu_freq:
            result += (
                f"  频率: 当前 {cpu_freq.current:.2f}MHz "
                f"(最大 {cpu_freq.max:.2f}MHz)\n"
            )

        return result

    def _get_memory_info(self) -> str:
        """获取内存信息"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        result = "💾 内存信息\n"
        result += (
            f"  物理内存: "
            f"{self._bytes_to_gb(mem.used):.2f}GB / "
            f"{self._bytes_to_gb(mem.total):.2f}GB "
            f"({mem.percent}%)\n"
        )
        result += (
            f"  可用内存: {self._bytes_to_gb(mem.available):.2f}GB\n"
        )
        result += (
            f"  交换分区: "
            f"{self._bytes_to_gb(swap.used):.2f}GB / "
            f"{self._bytes_to_gb(swap.total):.2f}GB "
            f"({swap.percent}%)\n"
        )

        return result

    def _get_disk_info(self) -> str:
        """获取磁盘信息"""
        result = "💿 磁盘信息\n"

        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                result += f"  {partition.device} ({partition.mountpoint})\n"
                result += (
                    f"    容量: "
                    f"{self._bytes_to_gb(usage.used):.2f}GB / "
                    f"{self._bytes_to_gb(usage.total):.2f}GB "
                    f"({usage.percent}%)\n"
                )
            except PermissionError:
                continue

        return result

    def _bytes_to_gb(self, bytes_value: int) -> float:
        """字节转GB"""
        return bytes_value / (1024 ** 3)


class TimeTool(Tool):
    """时间查询工具"""

    def __init__(self):
        super().__init__()
        self.name = "time"
        self.description = "查询当前时间和日期"
        self.category = "system"

        self.parameters = [
            ToolParameter(
                name="format",
                param_type="string",
                description=(
                    "返回格式: full(完整), date(仅日期), "
                    "time(仅时间), timestamp(时间戳)"
                ),
                required=False,
                default="full",
                enum=["full", "date", "time", "timestamp"]
            )
        ]

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行时间查询"""
        format_type = kwargs.get('format', 'full')

        try:
            now = datetime.now()

            if format_type == "full":
                result = now.strftime("%Y年%m月%d日 %H:%M:%S")
                weekdays = ['一', '二', '三', '四', '五', '六', '日']
                weekday = weekdays[now.weekday()]
                result += f" 星期{weekday}"

            elif format_type == "date":
                result = now.strftime("%Y年%m月%d日")
                weekdays = ['一', '二', '三', '四', '五', '六', '日']
                weekday = weekdays[now.weekday()]
                result += f" 星期{weekday}"

            elif format_type == "time":
                result = now.strftime("%H:%M:%S")

            elif format_type == "timestamp":
                result = str(int(now.timestamp()))

            return {
                'success': True,
                'result': f"⏰ 当前时间: {result}",
                'error': None
            }

        except Exception as e:
            logger.error(f"时间查询异常: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"查询异常: {str(e)}",
                'result': None
            }


class CalculatorTool(Tool):
    """计算器工具"""

    def __init__(self):
        super().__init__()
        self.name = "calculator"
        self.description = "执行数学计算（支持基本四则运算和常用数学函数）"
        self.category = "system"

        self.parameters = [
            ToolParameter(
                name="expression",
                param_type="string",
                description="数学表达式，如: 2+2, 10*5, sqrt(16), sin(0)",
                required=True
            )
        ]

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行计算"""
        expression = kwargs.get('expression', '')

        try:
            # 安全的数学运算环境
            import math
            safe_dict = {
                'abs': abs, 'round': round,
                'pow': pow, 'sum': sum,
                'min': min, 'max': max,
                # math模块函数
                'sqrt': math.sqrt, 'sin': math.sin,
                'cos': math.cos, 'tan': math.tan,
                'log': math.log, 'log10': math.log10,
                'exp': math.exp, 'pi': math.pi,
                'e': math.e
            }

            # 计算结果
            result = eval(expression, {"__builtins__": {}}, safe_dict)

            return {
                'success': True,
                'result': f"🧮 计算结果: {expression} = {result}",
                'error': None,
                'metadata': {
                    'expression': expression,
                    'value': result
                }
            }

        except Exception as e:
            logger.error(f"计算异常: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"计算失败: {str(e)}",
                'result': None
            }


# 创建工具实例
system_info_tool = SystemInfoTool()
time_tool = TimeTool()
calculator_tool = CalculatorTool()
