from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Dict, Any, Optional
import os
import time
import json
from dependencies import get_xiaole_agent
from agent import XiaoLeAgent
from modules.document_summarizer import DocumentSummarizer
from config import UPLOADS_DIR, DB_CONFIG
from auth import get_current_user

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)

# 初始化文档总结器
document_summarizer = DocumentSummarizer(
    db_config=DB_CONFIG,
    upload_dir=UPLOADS_DIR
)


def get_agent():
    return get_xiaole_agent()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """
    上传文档并自动总结
    """
    user_id = current_user
    start_time = time.time()
    doc_id = None

    try:
        # 验证文件
        file_content = await file.read()
        file_size = len(file_content)

        valid, file_type, error_msg = document_summarizer.validate_file(
            file.filename, file_size
        )

        if not valid:
            return {
                "success": False,
                "error": error_msg
            }

        # 生成唯一文件名
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file.filename}"

        # 确保 documents 子目录存在
        docs_dir = os.path.join(UPLOADS_DIR, "documents")
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir, exist_ok=True)

        file_path = os.path.join(docs_dir, safe_filename)

        # 保存文件
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # 创建数据库记录
        doc_id = document_summarizer.create_document_record(
            user_id=user_id,
            session_id=session_id or "",
            filename=safe_filename,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path
        )

        # 提取文本
        try:
            content = document_summarizer.extract_text(file_path, file_type)
            chunks = document_summarizer.split_text(content)

            # 更新内容
            document_summarizer.update_document_content(
                doc_id, content, len(chunks)
            )

            def governed_document_call(system_prompt, user_prompt, max_tokens=512):
                return agent._call_deepseek(
                    system_prompt, user_prompt, max_tokens=max_tokens,
                    caller="legacy.document_summary",
                    request_id=f"document:{doc_id}",
                    task_id=f"document:{doc_id}",
                )

            # 生成总结
            if len(chunks) == 1:
                summary = document_summarizer.summarize_chunk(
                    chunks[0],
                    governed_document_call
                )
            else:
                chunk_summaries = []
                for i, chunk in enumerate(chunks):
                    chunk_summary = document_summarizer.summarize_chunk(
                        chunk,
                        governed_document_call
                    )
                    chunk_summaries.append(chunk_summary)

                combined_text = "\n\n".join(chunk_summaries)
                if len(combined_text) > 4000:
                    summary = document_summarizer.summarize_chunk(
                        combined_text,
                        governed_document_call
                    )
                else:
                    summary = combined_text

            # 提取关键要点
            key_points = document_summarizer.extract_key_points(
                content,
                governed_document_call
            )

            # 更新总结结果
            processing_time = time.time() - start_time
            document_summarizer.update_document_summary(
                doc_id, summary, key_points, processing_time
            )

            # 存入记忆
            try:
                key_points_list = key_points if isinstance(
                    key_points, list) else []
                key_points_str = "\n".join([f"- {p}" for p in key_points_list])

                memory_content = (
                    f"【文档知识】用户上传了文档《{file.filename}》\n"
                    f"文档总结：\n{summary}\n\n"
                    f"关键要点：\n{key_points_str}"
                )

                agent.memory.remember(
                    content=memory_content,
                    tag=f"document:{file.filename}"
                )

                # 保存对话记录
                target_session_id = session_id
                if not target_session_id:
                    target_session_id = agent.conversation.create_session(
                        user_id=user_id,
                        title=f"文档总结：{file.filename}"
                    )

                agent.conversation.add_message(
                    session_id=target_session_id,
                    role="user",
                    content=f"📄 上传文档：{file.filename}"
                )

                ai_content = f"### 📄 文档总结：{file.filename}\n\n{summary}\n\n#### 💡 关键要点\n{key_points_str}"
                agent.conversation.add_message(
                    session_id=target_session_id,
                    role="assistant",
                    content=ai_content
                )

            except Exception as e:
                print(f"⚠️ 文档记忆/对话存储失败: {e}")

            return {
                "success": True,
                "document_id": doc_id,
                "session_id": target_session_id,
                "summary": summary,
                "key_points": key_points,
                "processing_time": processing_time,
                "content_length": len(content),
                "chunk_count": len(chunks)
            }

        except Exception as e:
            if doc_id:
                document_summarizer.mark_document_failed(doc_id, str(e))
            raise

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/{doc_id}")
def get_document_detail(doc_id: int):
    """获取文档详情"""
    try:
        doc = document_summarizer.get_document(doc_id)
        if not doc:
            return {
                "success": False,
                "error": "文档不存在"
            }

        return {
            "success": True,
            "document": doc
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/{doc_id}/export")
def export_document(doc_id: int, format: str = "md"):
    """导出文档总结"""
    try:
        doc = document_summarizer.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        content = f"""# {doc['filename']}

## 文档信息
- 文件大小: {doc['file_size'] / 1024:.2f} KB
- 处理时间: {doc['processing_time']:.1f}秒
- 分块数量: {doc['chunk_count']}

## 关键要点

"""
        key_points = doc.get('key_points', [])
        if isinstance(key_points, str):
            try:
                key_points = json.loads(key_points)
            except Exception:
                key_points = []

        for i, point in enumerate(key_points, 1):
            content += f"{i}. {point}\n"

        content += f"\n## 智能总结\n\n{doc['summary']}\n"

        from fastapi.responses import Response
        from urllib.parse import quote

        filename = f"{doc['original_filename']}_summary.md"
        encoded_filename = quote(filename)

        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
def get_user_documents(
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50
):
    """获取用户的文档列表"""
    try:
        docs = document_summarizer.get_user_documents(
            user_id, status, limit
        )

        return {
            "success": True,
            "documents": docs,
            "count": len(docs)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/{doc_id}")
def delete_document(doc_id: int):
    """删除文档"""
    try:
        success = document_summarizer.delete_document(doc_id)
        return {
            "success": success
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/admin/migrate_documents")
def migrate_documents(
    from_user: str = "default_user",
    to_user: str = "admin"
):
    """管理员接口:迁移文档从一个用户到另一个用户"""
    import psycopg2
    from config import DB_CONFIG

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 统计需要迁移的数量
        cur.execute(
            "SELECT COUNT(*) FROM documents WHERE user_id = %s",
            (from_user,)
        )
        count = cur.fetchone()[0]

        if count == 0:
            cur.close()
            conn.close()
            return {"migrated": 0, "message": "无需迁移"}

        # 执行迁移
        cur.execute(
            "UPDATE documents SET user_id = %s WHERE user_id = %s",
            (to_user, from_user)
        )
        conn.commit()
        cur.close()
        conn.close()

        return {
            "migrated": count,
            "message": f"成功迁移 {count} 个文档从 {from_user} 到 {to_user}"
        }
    except Exception as e:
        return {"error": str(e), "migrated": 0}
