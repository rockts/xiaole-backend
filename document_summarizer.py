"""
v0.8.0 Phase 3: 文档总结模块
支持PDF、DOCX、TXT、Markdown文件的上传、解析和智能总结
"""

import json
import logging
from typing import List, Optional, Tuple
from pathlib import Path

# 文件解析库
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# 数据库
import psycopg2
from psycopg2.extras import RealDictCursor

# OCR工具
from tools.baidu_ocr_tool import baidu_ocr_tool
try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

logger = logging.getLogger(__name__)


class DocumentSummarizer:
    """文档总结器：上传、解析、总结文档"""

    # 支持的文件类型
    # 注意：python-docx 不支持旧版 .doc 格式
    SUPPORTED_TYPES = {
        'pdf': ['.pdf'],
        'docx': ['.docx'],
        'txt': ['.txt'],
        'md': ['.md', '.markdown']
    }

    # 文件大小限制（字节）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    # 文本分块大小
    CHUNK_SIZE = 4000  # 每块4000字符

    def __init__(self, db_config: dict, upload_dir: str = "uploads"):
        """
        初始化文档总结器

        Args:
            db_config: 数据库配置
            upload_dir: 文件上传目录
        """
        self.db_config = db_config
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

        logger.info(f"文档总结器初始化完成，上传目录: {self.upload_dir}")

    def _get_connection(self):
        """获取数据库连接（UTF-8编码）"""
        conn = psycopg2.connect(**self.db_config, client_encoding='utf8')
        return conn

    def _sanitize_text(self, text: str) -> str:
        """移除文本中的NUL字符"""
        if not text:
            return text
        return text.replace('\x00', '')

    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str, str]:
        """
        验证文件类型和大小

        Args:
            filename: 文件名
            file_size: 文件大小（字节）

        Returns:
            (是否有效, 文件类型, 错误信息)
        """
        # 检查文件大小
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, '', f'文件过大，最大支持 {max_mb}MB'

        # 检查文件类型
        ext = Path(filename).suffix.lower()
        for file_type, extensions in self.SUPPORTED_TYPES.items():
            if ext in extensions:
                return True, file_type, ''

        supported = ', '.join([', '.join(exts)
                              for exts in self.SUPPORTED_TYPES.values()])
        return False, '', f'不支持的文件格式，支持: {supported}'

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        从PDF提取文本

        Args:
            file_path: PDF文件路径

        Returns:
            提取的文本内容
        """
        text = ""

        try:
            # 方法1: 使用pdfplumber（更准确）
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"

            if text.strip():
                logger.info(f"pdfplumber成功提取 {len(text)} 字符")
                return text.strip()

        except Exception as e:
            logger.warning(f"pdfplumber提取失败: {e}，尝试PyPDF2")

        try:
            # 方法2: 使用PyPDF2（备用）
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"

            logger.info(f"PyPDF2成功提取 {len(text)} 字符")
            return text.strip()

        except Exception as e:
            logger.error(f"PDF文本提取失败: {e}")

        # 如果常规提取失败或为空，尝试OCR
        if not text.strip():
            logger.info("常规提取为空，尝试OCR识别...")

            if not HAS_PDF2IMAGE:
                raise ValueError("无法进行OCR识别：缺少 pdf2image 库")

            if not baidu_ocr_tool.is_enabled():
                raise ValueError("无法进行OCR识别：百度OCR服务未配置")

            try:
                # 将PDF转为图片
                import io
                images = convert_from_path(file_path)
                ocr_text = []

                for i, image in enumerate(images):
                    logger.info(f"正在OCR识别第 {i+1}/{len(images)} 页...")
                    # 将PIL Image转为bytes
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG')
                    img_bytes = img_byte_arr.getvalue()

                    # 策略：优先尝试手写识别，如果失败或为空，回退到通用高精度识别
                    result = baidu_ocr_tool.recognize_handwriting(img_bytes)

                    # 检查是否需要回退 (失败 或 结果为空)
                    if not result['success'] or not result.get('text', '').strip():
                        logger.info(f"第 {i+1} 页手写识别效果不佳，切换到通用高精度识别...")
                        result = baidu_ocr_tool.recognize_general(img_bytes)

                    if result['success']:
                        text_content = result.get('text', '')
                        if text_content.strip():
                            ocr_text.append(text_content)
                            logger.info(
                                f"第 {i+1} 页识别成功 ({len(text_content)} 字符)")
                    else:
                        logger.warning(f"第 {i+1} 页识别失败: {result.get('error')}")

                full_text = "\n\n".join(ocr_text)
                if full_text.strip():
                    logger.info(f"OCR成功提取 {len(full_text)} 字符")
                    return full_text
                else:
                    raise ValueError("OCR识别结果为空")

            except Exception as e:
                error_msg = str(e)
                if "Unable to get page count" in error_msg or "poppler" in error_msg.lower():
                    raise ValueError(
                        "OCR识别需要安装 poppler 工具 (brew install poppler)")
                raise ValueError(f"OCR识别失败: {error_msg}")

        return text.strip()

    def extract_text_from_docx(self, file_path: str) -> str:
        """
        从DOCX提取文本

        Args:
            file_path: DOCX文件路径

        Returns:
            提取的文本内容
        """
        try:
            doc = Document(file_path)
            paragraphs = [
                para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n\n".join(paragraphs)

            logger.info(f"DOCX成功提取 {len(text)} 字符")
            return text.strip()

        except Exception as e:
            logger.error(f"DOCX文本提取失败: {e}")
            raise ValueError(f"无法提取DOCX文本: {str(e)}")

    def extract_text_from_txt(self, file_path: str) -> str:
        """
        从TXT/MD提取文本

        Args:
            file_path: 文本文件路径

        Returns:
            提取的文本内容
        """
        try:
            # 先尝试常用编码（快速路径）
            common_encodings = ['utf-8', 'gbk', 'gb2312']

            for encoding in common_encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                        text = f.read()
                    logger.info(
                        f"TXT成功提取 {len(text)} 字符（编码: {encoding}）"
                    )
                    return text.strip()
                except (UnicodeDecodeError, UnicodeError):
                    continue

            # 如果常用编码都失败，尝试更多编码
            additional_encodings = [
                'utf-16', 'utf-16-le', 'utf-16-be',
                'gb18030', 'big5', 'ascii',
                'latin-1', 'iso-8859-1'
            ]

            for encoding in additional_encodings:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                        text = f.read()
                    logger.info(
                        f"TXT成功提取 {len(text)} 字符（编码: {encoding}）"
                    )
                    return text.strip()
                except (UnicodeDecodeError, UnicodeError):
                    continue

            # 最后尝试：忽略错误字符
            logger.warning("使用UTF-8编码并忽略错误字符")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            if text.strip():
                logger.info(f"TXT提取 {len(text)} 字符（UTF-8 + 忽略错误）")
                return text.strip()

            raise ValueError("文件内容为空或无法读取")

        except Exception as e:
            logger.error(f"TXT文本提取失败: {e}")
            raise ValueError(f"无法提取文本: {str(e)}")

    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        根据文件类型提取文本

        Args:
            file_path: 文件路径
            file_type: 文件类型 (pdf/docx/txt/md)

        Returns:
            提取的文本内容
        """
        if file_type == 'pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_type == 'docx':
            text = self.extract_text_from_docx(file_path)
        elif file_type in ['txt', 'md']:
            text = self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

        if not text or not text.strip():
            raise ValueError("无法提取文本内容（可能是扫描件或纯图片文档）")

        return self._sanitize_text(text)

    def split_text(self, text: str, chunk_size: int = None) -> List[str]:
        """
        将长文本分块

        Args:
            text: 原始文本
            chunk_size: 每块大小（字符数）

        Returns:
            文本块列表
        """
        if chunk_size is None:
            chunk_size = self.CHUNK_SIZE

        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果单个段落就超过块大小，强制分割
            if len(para) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 强制分割长段落
                for i in range(0, len(para), chunk_size):
                    chunks.append(para[i:i+chunk_size])

            # 累积段落到当前块
            elif len(current_chunk) + len(para) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

            # 当前块已满，开始新块
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para

        # 添加最后一块
        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"文本分块完成: {len(text)} 字符 → {len(chunks)} 块")
        return chunks

    def summarize_chunk(self, text: str, ai_summarizer) -> str:
        """
        总结单个文本块（由AI完成）

        Args:
            text: 文本块
            ai_summarizer: AI总结函数 (system_prompt, user_prompt)

        Returns:
            总结文本
        """
        system_prompt = "你是一个专业的文档总结助手，擅长提取核心信息。"
        user_prompt = f"""请对以下文本进行简洁总结，保留关键信息：

{text}

总结要求：
1. 简洁明了，保留核心观点
2. 提取关键数据和事实
3. 保持逻辑连贯
4. 不超过原文的1/3长度

总结："""

        return ai_summarizer(system_prompt, user_prompt)

    def extract_key_points(self, text: str, ai_analyzer) -> List[str]:
        """
        提取关键要点（由AI完成）

        Args:
            text: 文本内容
            ai_analyzer: AI分析函数 (system_prompt, user_prompt)

        Returns:
            关键要点列表
        """
        system_prompt = "你是一个专业的文档分析助手，擅长提取关键信息。"
        user_prompt = f"""请从以下文本中提取5-10个关键要点：

{text[:2000]}  # 只用前2000字符

要求：
1. 每个要点一句话
2. 突出核心信息
3. 按重要性排序

请以JSON数组格式返回，例如：
["要点1", "要点2", "要点3"]

关键要点："""

        result = ai_analyzer(system_prompt, user_prompt)

        # 尝试解析JSON
        try:
            import re
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                points = json.loads(json_match.group())
                return points
        except Exception:
            pass

        # 解析失败，按行分割
        return [line.strip('- ').strip()
                for line in result.split('\n')
                if line.strip()][:10]

    def create_document_record(
        self,
        user_id: str,
        session_id: str,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        file_path: str
    ) -> int:
        """
        创建文档记录

        Returns:
            文档ID
        """
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO documents (
                    user_id, session_id, filename, original_filename,
                    file_type, file_size, file_path, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
            """, (user_id, session_id, filename, original_filename,
                  file_type, file_size, file_path))

            doc_id = cur.fetchone()[0]
            conn.commit()

            logger.info(f"创建文档记录: ID={doc_id}, 文件={original_filename}")
            return doc_id

        finally:
            cur.close()
            conn.close()

    def update_document_content(
        self,
        doc_id: int,
        content: str,
        chunk_count: int
    ):
        """更新文档内容"""
        conn = self._get_connection()
        cur = conn.cursor()

        # Sanitize content
        content = self._sanitize_text(content)

        try:
            cur.execute("""
                UPDATE documents
                SET content = %s,
                    content_length = %s,
                    chunk_count = %s,
                    status = 'processing'
                WHERE id = %s
            """, (content, len(content), chunk_count, doc_id))

            conn.commit()
            logger.info(f"更新文档内容: ID={doc_id}, 长度={len(content)}")

        finally:
            cur.close()
            conn.close()

    def update_document_summary(
        self,
        doc_id: int,
        summary: str,
        key_points: List[str],
        processing_time: float
    ):
        """更新文档总结"""
        conn = self._get_connection()
        cur = conn.cursor()

        # Sanitize summary and key_points
        summary = self._sanitize_text(summary)
        key_points = [self._sanitize_text(p) for p in key_points]

        try:
            cur.execute("""
                UPDATE documents
                SET summary = %s,
                    summary_length = %s,
                    key_points = %s,
                    processing_time = %s,
                    status = 'completed',
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (summary, len(summary), json.dumps(key_points, ensure_ascii=False),
                  processing_time, doc_id))

            conn.commit()
            logger.info(f"更新文档总结: ID={doc_id}, 耗时={processing_time:.2f}s")

        finally:
            cur.close()
            conn.close()

    def mark_document_failed(self, doc_id: int, error_message: str):
        """标记文档处理失败"""
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE documents
                SET status = 'failed',
                    error_message = %s
                WHERE id = %s
            """, (error_message, doc_id))

            conn.commit()
            logger.error(f"文档处理失败: ID={doc_id}, 错误={error_message}")

        finally:
            cur.close()
            conn.close()

    def get_document(self, doc_id: int) -> Optional[dict]:
        """获取文档详情"""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute("""
                SELECT * FROM documents WHERE id = %s
            """, (doc_id,))

            doc = cur.fetchone()
            if doc:
                # 解析JSON字段
                if doc['key_points']:
                    try:
                        doc['key_points'] = json.loads(doc['key_points'])
                    except Exception:
                        doc['key_points'] = []
                return dict(doc)

            return None

        finally:
            cur.close()
            conn.close()

    def get_user_documents(
        self,
        user_id: str,
        status: str = None,
        limit: int = 50
    ) -> List[dict]:
        """获取用户的文档列表"""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            if status:
                cur.execute("""
                    SELECT id, user_id, session_id, filename, original_filename,
                           file_type, file_size, content_length, summary_length,
                           chunk_count, processing_time, status, created_at, completed_at
                    FROM documents
                    WHERE user_id = %s AND status = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, status, limit))
            else:
                cur.execute("""
                    SELECT id, user_id, session_id, filename, original_filename,
                           file_type, file_size, content_length, summary_length,
                           chunk_count, processing_time, status, created_at, completed_at
                    FROM documents
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))

            docs = cur.fetchall()
            return [dict(doc) for doc in docs]

        finally:
            cur.close()
            conn.close()

    def delete_document(self, doc_id: int) -> bool:
        """删除文档（包括文件）"""
        # 先获取文件路径
        doc = self.get_document(doc_id)
        if not doc:
            return False

        # 删除文件
        try:
            file_path = Path(doc['file_path'])
            if file_path.exists():
                file_path.unlink()
                logger.info(f"删除文件: {file_path}")
        except Exception as e:
            logger.warning(f"删除文件失败: {e}")

        # 删除数据库记录
        conn = self._get_connection()
        cur = conn.cursor()

        try:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            conn.commit()
            logger.info(f"删除文档记录: ID={doc_id}")
            return True

        finally:
            cur.close()
            conn.close()
