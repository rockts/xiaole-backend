"""
文件操作工具
支持文件读取、写入、列表、搜索等功能
包含安全限制：路径白名单、文件类型限制、大小限制
"""
import asyncio
import os
import glob
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional
from tool_manager import Tool, ToolParameter

# 尝试导入文档处理库
try:
    import PyPDF2
    import pdfplumber
    from docx import Document as DocxDocument
    HAS_DOC_LIBS = True
except ImportError:
    HAS_DOC_LIBS = False


class FileTool(Tool):
    """文件操作工具"""

    # 安全配置
    # 获取项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent

    ALLOWED_DIRS = [
        str(PROJECT_ROOT / "files"),  # 项目下的files目录
        str(PROJECT_ROOT / "backend" / "uploads"),  # 上传文件的目录
        "/tmp/xiaole_files",  # 备用临时目录
    ]

    ALLOWED_EXTENSIONS = [
        ".txt", ".md", ".json", ".csv",
        ".log", ".xml", ".yaml", ".yml",
        ".py", ".js", ".html", ".css",
        ".pdf", ".docx"  # 支持文档格式
    ]

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_SEARCH_RESULTS = 100

    def __init__(self):
        super().__init__()
        self.name = "file"
        self.description = "文件操作工具，支持读取、写入、列表、搜索文件"
        self.parameters = [
            ToolParameter(
                name="operation",
                param_type="string",
                description=(
                    "操作类型: read(读取), write(写入), "
                    "list(列表), search(搜索)"
                ),
                required=True,
                enum=["read", "write", "list", "search"]
            ),
            ToolParameter(
                name="path",
                param_type="string",
                description="文件或目录路径（相对于允许的目录）",
                required=True
            ),
            ToolParameter(
                name="content",
                param_type="string",
                description="写入的内容（仅用于write操作）",
                required=False
            ),
            ToolParameter(
                name="pattern",
                param_type="string",
                description="搜索模式（仅用于search操作，支持通配符如*.txt）",
                required=False
            ),
            ToolParameter(
                name="recursive",
                param_type="boolean",
                description="是否递归搜索（仅用于list和search操作）",
                required=False,
                default=False
            )
        ]

        # 确保默认工作目录存在
        self._ensure_default_dir()

    def _ensure_default_dir(self):
        """确保默认工作目录存在"""
        default_dir = self.ALLOWED_DIRS[0]
        os.makedirs(default_dir, exist_ok=True)

    def _resolve_path(self, path: str) -> Optional[Path]:
        """
        解析并验证路径
        返回绝对路径或None（如果路径不安全）
        """
        # 如果是相对路径，使用默认目录
        if not os.path.isabs(path):
            path = os.path.join(self.ALLOWED_DIRS[0], path)

        # 规范化路径
        resolved = Path(path).resolve()

        # 检查是否在允许的目录内
        for allowed_dir in self.ALLOWED_DIRS:
            allowed_path = Path(allowed_dir).resolve()
            try:
                resolved.relative_to(allowed_path)
                return resolved
            except ValueError:
                continue

        return None

    def _check_extension(self, path: Path) -> bool:
        """检查文件扩展名是否允许"""
        return path.suffix.lower() in self.ALLOWED_EXTENSIONS

    def _check_size(self, path: Path) -> bool:
        """检查文件大小是否超过限制"""
        if not path.exists():
            return True
        return path.stat().st_size <= self.MAX_FILE_SIZE

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行文件操作"""
        operation = kwargs.get("operation")
        path_str = kwargs.get("path")

        if not operation or not path_str:
            return {
                "success": False,
                "error": "缺少必要参数: operation 和 path"
            }

        # 验证操作类型
        valid_operations = ["read", "write", "list", "search"]
        if operation not in valid_operations:
            return {
                "success": False,
                "error": (
                    f"无效的操作类型: {operation}，"
                    f"支持: {', '.join(valid_operations)}"
                )
            }

        # 解析路径
        path = self._resolve_path(path_str)
        if not path:
            return {
                "success": False,
                "error": f"路径不安全或不在允许的目录内: {path_str}"
            }

        # 执行对应操作
        try:
            if operation == "read":
                return await self._read_file(path)
            elif operation == "write":
                content = kwargs.get("content", "")
                return await self._write_file(path, content)
            elif operation == "list":
                recursive = kwargs.get("recursive", False)
                return await self._list_files(path, recursive)
            elif operation == "search":
                pattern = kwargs.get("pattern", "*")
                recursive = kwargs.get("recursive", False)
                return await self._search_files(path, pattern, recursive)
        except Exception as e:
            return {
                "success": False,
                "error": f"执行 {operation} 操作时出错: {str(e)}"
            }

    def _read_pdf(self, path: Path) -> str:
        """读取PDF文件内容"""
        text = ""
        try:
            # 优先使用 pdfplumber
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text.strip()
        except Exception:
            # 降级使用 PyPDF2
            try:
                with open(path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n\n"
                return text.strip()
            except Exception as e:
                raise ValueError(f"读取PDF失败: {str(e)}")

    def _read_docx(self, path: Path) -> str:
        """读取DOCX文件内容"""
        try:
            doc = DocxDocument(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            raise ValueError(f"读取DOCX失败: {str(e)}")

    async def _read_file(self, path: Path) -> Dict[str, Any]:
        """读取文件内容"""
        # 智能查找：如果文件不存在，尝试在 uploads 目录查找（处理时间戳前缀）
        if not path.exists():
            # 尝试查找 uploads 目录下的同名文件（忽略前缀）
            filename = path.name
            uploads_dir = self.PROJECT_ROOT / "backend" / "uploads"

            if uploads_dir.exists():
                # 查找以 _filename 结尾的文件
                found_files = list(uploads_dir.glob(f"*_{filename}"))
                if found_files:
                    # 找到匹配的文件，使用最新的一个
                    found_files.sort(
                        key=lambda x: x.stat().st_mtime, reverse=True
                    )
                    path = found_files[0]
                    # 重新验证路径安全性
                    if not self._resolve_path(str(path)):
                        return {
                            "success": False,
                            "error": f"找到文件但路径不安全: {path}"
                        }

        if not path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {path}"
            }

        if not path.is_file():
            return {
                "success": False,
                "error": f"不是文件: {path}"
            }

        if not self._check_extension(path):
            return {
                "success": False,
                "error": f"不支持的文件类型: {path.suffix}"
            }

        if not self._check_size(path):
            return {
                "success": False,
                "error": f"文件过大（超过{self.MAX_FILE_SIZE / 1024 / 1024}MB）"
            }

        # 检查是否是文档类型
        suffix = path.suffix.lower()
        if suffix in ['.pdf', '.docx']:
            if not HAS_DOC_LIBS:
                return {
                    "success": False,
                    "error": "未安装文档处理库(pdfplumber, python-docx)，无法读取PDF/DOCX"
                }

            try:
                content = ""
                if suffix == '.pdf':
                    content = await asyncio.to_thread(self._read_pdf, path)
                elif suffix == '.docx':
                    content = await asyncio.to_thread(self._read_docx, path)

                return {
                    "success": True,
                    "operation": "read",
                    "path": str(path),
                    "content": content,
                    "size": path.stat().st_size,
                    "lines": len(content.splitlines())
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        try:
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()

            return {
                "success": True,
                "operation": "read",
                "path": str(path),
                "content": content,
                "size": path.stat().st_size,
                "lines": len(content.splitlines())
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "文件编码错误，仅支持UTF-8编码"
            }

    async def _write_file(self, path: Path, content: str) -> Dict[str, Any]:
        """写入文件内容"""
        if not self._check_extension(path):
            return {
                "success": False,
                "error": f"不支持的文件类型: {path.suffix}"
            }

        # 检查内容大小
        content_size = len(content.encode('utf-8'))
        if content_size > self.MAX_FILE_SIZE:
            return {
                "success": False,
                "error": f"内容过大（超过{self.MAX_FILE_SIZE / 1024 / 1024}MB）"
            }

        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(content)

            return {
                "success": True,
                "operation": "write",
                "path": str(path),
                "size": path.stat().st_size,
                "lines": len(content.splitlines()),
                "message": f"成功写入文件: {path.name}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"写入文件失败: {str(e)}"
            }

    async def _list_files(
        self, path: Path, recursive: bool = False
    ) -> Dict[str, Any]:
        """列出目录内容"""
        if not path.exists():
            return {
                "success": False,
                "error": f"路径不存在: {path}"
            }

        if not path.is_dir():
            return {
                "success": False,
                "error": f"不是目录: {path}"
            }

        try:
            files = []
            dirs = []

            if recursive:
                # 递归遍历
                for item in path.rglob("*"):
                    if item.is_file():
                        files.append({
                            "name": item.name,
                            "path": str(item.relative_to(path)),
                            "size": item.stat().st_size,
                            "extension": item.suffix
                        })
                    elif item.is_dir():
                        dirs.append({
                            "name": item.name,
                            "path": str(item.relative_to(path))
                        })
            else:
                # 仅列出当前目录
                for item in path.iterdir():
                    if item.is_file():
                        files.append({
                            "name": item.name,
                            "size": item.stat().st_size,
                            "extension": item.suffix
                        })
                    elif item.is_dir():
                        dirs.append({
                            "name": item.name
                        })

            return {
                "success": True,
                "operation": "list",
                "path": str(path),
                "files": files,
                "directories": dirs,
                "file_count": len(files),
                "dir_count": len(dirs)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"列出目录失败: {str(e)}"
            }

    async def _search_files(
        self, path: Path, pattern: str, recursive: bool = False
    ) -> Dict[str, Any]:
        """搜索文件"""
        if not path.exists():
            return {
                "success": False,
                "error": f"路径不存在: {path}"
            }

        if not path.is_dir():
            return {
                "success": False,
                "error": f"不是目录: {path}"
            }

        try:
            # 构建搜索模式
            if recursive:
                search_pattern = str(path / "**" / pattern)
            else:
                search_pattern = str(path / pattern)

            # 执行搜索
            found_files = []
            for file_path in glob.glob(search_pattern, recursive=recursive):
                file_path = Path(file_path)
                if file_path.is_file():
                    # 计算相对路径
                    rel_path = (
                        str(file_path.relative_to(path))
                        if recursive else file_path.name
                    )
                    found_files.append({
                        "name": file_path.name,
                        "path": rel_path,
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix
                    })

                    # 限制结果数量
                    if len(found_files) >= self.MAX_SEARCH_RESULTS:
                        break

            return {
                "success": True,
                "operation": "search",
                "path": str(path),
                "pattern": pattern,
                "recursive": recursive,
                "results": found_files,
                "count": len(found_files),
                "truncated": len(found_files) >= self.MAX_SEARCH_RESULTS
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"搜索文件失败: {str(e)}"
            }


# 创建工具实例
file_tool = FileTool()
