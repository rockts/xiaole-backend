from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
from pydantic import BaseModel
from dependencies import get_xiaole_agent, get_proactive_qa
from agent import XiaoLeAgent
from modules.proactive_qa import ProactiveQA
from auth import get_current_user
from logger import logger


# 请求体模型（用于接收POST body中的图片路径）
class ChatBody(BaseModel):
    image_path: Optional[str] = None


router = APIRouter(
    prefix="",
    tags=["chat"]
)


def get_agent():
    return get_xiaole_agent()


def get_qa():
    return get_proactive_qa()


def _looks_like_time_reply(text: Optional[str]) -> bool:
    if not text:
        return False
    time_keywords = ["现在是", "今天是", "当前时间", "目前是", "此刻是"]
    date_keywords = ["日期", "星期", "周几"]
    indicators = time_keywords + date_keywords
    return any(keyword in text for keyword in indicators)


@router.post("/chat")
def chat(
    prompt: str,
    session_id: Optional[str] = None,
    user_id: str = "default_user",
    response_style: str = "balanced",
    memorize: bool = False,
    # 允许从query/form中回退读取image_path，避免前端未传JSON body时失效
    image_path: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent),
    qa: ProactiveQA = Depends(get_qa),
    body: Optional[ChatBody] = None
):
    """支持上下文的对话接口"""
    # 使用认证用户ID覆盖请求中的user_id
    user_id = current_user

    # 从body中获取image_path；若无，则回退使用query/form中的image_path
    body_image_path = None
    try:
        body_image_path = body.image_path if body else None
    except Exception:
        body_image_path = None

    effective_image_path = body_image_path or image_path

    if effective_image_path:
        logger.info(
            "📷 收到图片路径: raw='%s' (body='%s', query='%s')",
            effective_image_path,
            body_image_path,
            image_path,
        )

    # 如果有图片，先进行图片识别
    if effective_image_path:
        try:
            # 修正：确保能正确导入 VisionTool
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.dirname(current_dir)
            project_root = os.path.dirname(backend_dir)
            if project_root not in sys.path:
                sys.path.append(project_root)

            from tools.vision_tool import VisionTool
            vision_tool = VisionTool()

            logger.info("🔍 开始图片识别流程: %s", effective_image_path)
            # 智能选择识别prompt
            important_kw = ['课程表', '课表', '时间表', '上课']
            if prompt and any(kw in prompt for kw in important_kw):
                ocr_prompt = '''这是一张学生课程表。请仔细识别表格中的内容：
1. 表头有：星期一、星期二、星期三、星期四、星期五
2. 左侧行标题有：晨读、第1节、第2节...第7节、午休、课后辅导
3. 每个格子可能有课程名称（如"科学"）和编号（如"(5)"）

请完整地列出每一天的所有课程，包括空格子（标注"无课"）。
格式：
周一：晨读-XX, 第1节-XX, 第2节-XX...
周二：...
依此类推。不要省略任何信息。'''
            else:
                ocr_prompt = (
                    '请详细描述这张图片的内容，包括：\n'
                    '1. 主体物品或场景是什么\n'
                    '2. 图片中的文字信息（如有），如看到片段"ckin/ickin"等，可推测完整品牌名\n'
                    '3. 颜色、品牌、标识等细节\n'
                    '4. 其他值得注意的特征\n\n'
                    '如能识别品牌请直接说明。\n\n'
                    '重要：如果图片中包含数学公式、LaTeX 符号或特殊字符，请保持原始格式，'
                    '不要拆分或修改数学符号。例如：$\\alpha$、$\\beta$、$\\gamma$ 等应保持完整。'
                )

            # 添加超时保护，避免图片识别卡住导致请求超时
            import threading
            import time

            vision_result = None
            vision_error = None
            vision_completed = threading.Event()

            def analyze_with_timeout():
                nonlocal vision_result, vision_error
                try:
                    logger.info("🔄 开始执行图片识别...")
                    result = vision_tool.analyze_image(
                        image_path=effective_image_path,
                        prompt=ocr_prompt,
                        prefer_model="auto"
                    )
                    # 确保返回的是字典类型
                    if result is None:
                        logger.error("❌ analyze_image 返回了 None")
                        vision_result = {
                            "success": False,
                            "error": "图片识别返回空结果"
                        }
                    elif not isinstance(result, dict):
                        logger.error(
                            "❌ analyze_image 返回了非字典类型: %s",
                            type(result)
                        )
                        vision_result = {
                            "success": False,
                            "error": f"图片识别返回了无效类型: {type(result)}"
                        }
                    else:
                        vision_result = result
                        logger.info(
                            "✅ 图片识别执行完成: success=%s",
                            vision_result.get('success')
                        )
                except Exception as e:
                    vision_error = str(e)
                    logger.error(
                        "❌ 图片识别过程中异常: %s", e, exc_info=True
                    )
                    vision_result = {"success": False, "error": str(e)}
                finally:
                    vision_completed.set()

            # 在单独线程中执行，避免阻塞
            analyze_thread = threading.Thread(
                target=analyze_with_timeout, daemon=True
            )
            start_time = time.time()
            analyze_thread.start()

            # 等待完成或超时
            completed = vision_completed.wait(timeout=30)  # 30秒超时

            elapsed = time.time() - start_time

            if not completed:
                logger.error("❌ 图片识别超时（%.1f秒）", elapsed)
                vision_result = {
                    "success": False,
                    "error": "图片识别超时，请稍后重试"
                }
            elif vision_error and (
                not vision_result or not isinstance(vision_result, dict)
            ):
                vision_result = {"success": False, "error": vision_error}
            elif not vision_result or not isinstance(vision_result, dict):
                logger.warning(
                    "⚠️ 图片识别未返回结果: vision_result=%s, type=%s",
                    vision_result, type(vision_result)
                )
                vision_result = {
                    "success": False,
                    "error": "图片识别未返回结果"
                }

            logger.info("✅ 图片识别完成: success=%s, model=%s, error=%s",
                        vision_result.get('success'),
                        vision_result.get('model', 'unknown'),
                        vision_result.get('error') if not vision_result.get('success') else None)

            if vision_result and vision_result.get('success'):
                vision_description = vision_result.get('description', '')

                safety_instruction = (
                    "【视觉回答要求】请严格基于 <vision_result> 中的内容作答。"
                    "禁止输出与图片无关的回答，尤其禁止回复当前时间、日期或泛泛的寒暄。"
                    "当用户提问'这是什么/这是谁/这张图是什么'等时，必须直接描述图像主体、文字和关键细节。\n"
                    "重要：如果 <vision_result> 中包含数学公式、LaTeX 符号（如 $\\alpha$、$\\beta$、$\\gamma$ 等），"
                    "请保持原始格式，不要拆分、修改或转义这些符号。直接使用原始格式输出。"
                )

                if prompt:
                    combined_prompt = (
                        f"{safety_instruction}\n"
                        f"<vision_result>\n"
                        f"我通过视觉能力识别到的图片内容：\n"
                        f"{vision_description}\n"
                        f"</vision_result>\n\n"
                        f"用户问题：{prompt}\n\n"
                        f"请基于我识别到的图片内容回答用户的问题。"
                        f"如果识别到品牌相关的文字片段（如'ckin'、'kin'等），请结合常见品牌推理出完整品牌名。"
                        f"直接回答用户的实际问题，不要说'这不是XXX'。"
                    )
                else:
                    combined_prompt = (
                        f"{safety_instruction}\n"
                        f"<vision_result>\n"
                        f"我通过视觉能力识别到的图片内容：\n"
                        f"{vision_description}\n"
                        f"</vision_result>\n\n"
                        f"请分析并解释这张图片的内容。"
                    )

                should_memorize = memorize
                if prompt:
                    memorize_keywords = ['记住', '保存', '记下', '存一下', '记录']
                    relation_keywords = ['我的', '我儿子', '我女儿', '我妻子', '我老婆',
                                         '我老公', '我爸', '我妈', '家人', '孩子', '宝宝']

                    should_memorize = should_memorize or any(
                        kw in prompt for kw in memorize_keywords)
                    should_memorize = should_memorize or any(
                        kw in prompt for kw in relation_keywords)

                if not should_memorize:
                    important_content_indicators = [
                        '课程表', '时间表', '日程', '表格', '证件']
                    should_memorize = any(
                        ind in vision_description
                        for ind in important_content_indicators
                    )

                if should_memorize:
                    try:
                        # 使用 effective_image_path 而不是 image_path
                        filename = effective_image_path.split(
                            '/')[-1] if effective_image_path else 'unknown'
                        agent.memory.remember(
                            content=vision_description,
                            tag=f"image:{filename}"
                        )
                        combined_prompt += "\n\n[系统提示：这张图片的内容我已经记住了，以后可以回忆]"
                    except Exception as e:
                        logger.error(f"⚠️ 保存图片记忆失败: {e}")

                # 图片识别已完成,但仍需传递image_path以保存到消息中供前端显示
                agent_result = agent.chat(
                    combined_prompt, session_id, user_id, response_style,
                    image_path=effective_image_path,  # 保存图片路径供前端显示
                    original_user_prompt=prompt
                )

                logger.info(
                    "🔍 Agent返回结果类型: %s, 内容前100字: %s",
                    type(agent_result).__name__,
                    str(agent_result)[:100] if agent_result else "None"
                )

                fallback_reply = (
                    "这是系统刚刚识别出的图片内容：\n"
                    f"{vision_description.strip()}\n"
                    "(由视觉识别直接生成)"
                )

                if isinstance(agent_result, dict):
                    reply_text = agent_result.get('reply', '')
                    logger.info("🔍 检测reply是否像时间: %s, 内容: %s",
                                _looks_like_time_reply(reply_text),
                                reply_text[:100])
                    if _looks_like_time_reply(reply_text):
                        logger.warning("⚠️ 触发fallback替换!")
                        agent_result['reply'] = fallback_reply
                elif isinstance(agent_result, str):
                    logger.info("🔍 检测字符串是否像时间: %s, 内容: %s",
                                _looks_like_time_reply(agent_result),
                                agent_result[:100])
                    if _looks_like_time_reply(agent_result):
                        logger.warning("⚠️ 触发fallback替换!")
                        agent_result = fallback_reply

                return agent_result
            else:
                error_msg = vision_result.get(
                    'error', '未知错误') if vision_result else '图片识别失败'
                logger.error("❌ 图片识别失败: %s", error_msg)
                # 降级处理：调用 agent.chat 确保用户消息被保存
                # 重要：在 prompt 中明确告诉 agent 不要再次调用 vision 工具
                try:
                    fallback_prompt = (
                        f"{prompt}\n"
                        f"[系统提示：用户上传了图片，但图片识别已失败: {error_msg}。"
                        f"请直接回答用户的问题，不要再次尝试调用 vision_analysis 工具。"
                        f"如果无法识别图片内容，请礼貌地告知用户图片识别失败，建议稍后重试或描述图片内容。]"
                    )
                    return agent.chat(
                        fallback_prompt,
                        session_id, user_id, response_style,
                        image_path=effective_image_path,
                        original_user_prompt=prompt
                    )
                except Exception as agent_error:
                    logger.error(f"❌ 降级处理也失败: {agent_error}", exc_info=True)
                    # 最后的安全返回
                    return {
                        "reply": f"抱歉，图片识别失败：{error_msg}。请稍后重试，或者您可以描述一下图片内容，我来帮您分析。",
                        "session_id": session_id,
                        "error": error_msg
                    }
        except Exception as e:
            logger.error("❌ 图片处理异常: %s", str(e), exc_info=True)
            # 降级处理：调用 agent.chat 确保用户消息被保存
            # 重要：在 prompt 中明确告诉 agent 不要再次调用 vision 工具
            try:
                fallback_prompt = (
                    f"{prompt}\n"
                    f"[系统提示：用户上传了图片，但图片处理出错: {str(e)}。"
                    f"请直接回答用户的问题，不要再次尝试调用 vision_analysis 工具。"
                    f"如果无法识别图片内容，请礼貌地告知用户图片处理出错，建议稍后重试或描述图片内容。]"
                )
                return agent.chat(
                    fallback_prompt,
                    session_id, user_id, response_style,
                    image_path=effective_image_path,
                    original_user_prompt=prompt
                )
            except Exception as agent_error:
                logger.error(f"❌ 降级处理也失败: {agent_error}", exc_info=True)
                # 最后的安全返回
                return {
                    "reply": f"抱歉，处理图片时出现了错误：{str(e)}。请稍后重试，或者您可以描述一下图片内容，我来帮您分析。",
                    "session_id": session_id,
                    "error": str(e)
                }

    result = agent.chat(prompt, session_id, user_id, response_style)

    try:
        actual_session_id = result.get('session_id') if isinstance(
            result, dict) else session_id

        if actual_session_id:
            try:
                qa.analyze_conversation(actual_session_id, user_id)
            except Exception as e:
                logger.error(f"⚠️ 追问分析异常: {e}")
    except Exception as e:
        logger.error(f"⚠️ 追问模块异常: {e}")

    return result


@router.post("/chat/stream")
def chat_stream(
    prompt: str,
    session_id: Optional[str] = None,
    user_id: str = "default_user",
    response_style: str = "balanced",
    memorize: bool = False,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent),
    qa: ProactiveQA = Depends(get_qa),
    body: Optional[ChatBody] = None
):
    """流式对话接口（SSE 兼容）。

    说明：
    - 为尽快上线体验，当前实现为"切片流"：先生成完整回复，再按块推送；
      命中直达规则（时间/日期/计算/小名等）时能即时返回；
    - 后续可改为直连模型原生流式（DeepSeek/Claude）。
    """
    # 使用认证后的用户名作为user_id,支持多用户
    user_id = current_user

    # 从body中获取image_path
    image_path = body.image_path if body else None

    logger.info(
        f"📥 Stream收到请求 - session_id: {session_id}, "
        f"user_id: {user_id}, prompt: {prompt[:50]}"
    )

    def event_stream():
        import json
        # 起始事件，便于前端建立状态
        start_payload = {"type": "start"}
        yield f"data: {json.dumps(start_payload, ensure_ascii=False)}\n\n"

        # 处理图片（沿用同步路径，保持稳定）
        if image_path:
            # 发送处理中提示，防止连接超时
            loading_msg = {'type': 'delta', 'data': '正在分析图片内容，请稍候...\n\n'}
            yield f"data: {json.dumps(loading_msg, ensure_ascii=False)}\n\n"

            try:
                # 修正：确保能正确导入 VisionTool
                import sys
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                backend_dir = os.path.dirname(current_dir)
                project_root = os.path.dirname(backend_dir)
                if project_root not in sys.path:
                    sys.path.append(project_root)

                from tools.vision_tool import VisionTool
                vision_tool = VisionTool()
                try:
                    important_kw = ['课程表', '课表', '时间表', '上课']
                    if prompt and any(kw in prompt for kw in important_kw):
                        ocr_prompt = '这是一张课程表，请识别并按天/节次列出。'
                    else:
                        ocr_prompt = '请详细描述这张图片的内容（主体/文字/颜色/品牌等）。'

                    # 使用线程池执行耗时操作，同时发送心跳包
                    import concurrent.futures
                    import time

                    vision_result = {}
                    heartbeat_count = 0
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            vision_tool.analyze_image,
                            image_path=image_path,
                            prompt=ocr_prompt,
                            prefer_model="auto"
                        )

                        # 等待结果，每5秒发送一次心跳
                        while not future.done():
                            time.sleep(5)
                            heartbeat_count += 1
                            # 发送进度提示，让用户知道还在处理
                            progress_msg = {
                                'type': 'delta',
                                'data': '.' if heartbeat_count % 3 != 0 else ''
                            }
                            chunk = json.dumps(
                                progress_msg, ensure_ascii=False)
                            yield f"data: {chunk}\n\n"

                        vision_result = future.result()

                    if vision_result.get('success'):
                        desc = vision_result.get('description', '')
                        safety_instruction = (
                            "【视觉回答要求】请严格基于 <vision_result> 中的内容作答。"
                            "禁止输出与图片无关的回答，尤其禁止回复当前时间、日期或泛泛的寒暄。"
                            "当用户提问'这是什么/这是谁/这张图是什么'等时，必须直接描述图像主体、文字和关键细节。\n"
                            "重要：如果 <vision_result> 中包含数学公式、LaTeX 符号（如 $\\alpha$、$\\beta$、$\\gamma$ 等），"
                            "请保持原始格式，不要拆分、修改或转义这些符号。直接使用原始格式输出。"
                        )

                        if prompt:
                            combined_prompt = (
                                f"{safety_instruction}\n"
                                f"<vision_result>\n{desc}\n</vision_result>\n\n"
                                f"用户问题：{prompt}\n\n请基于识别结果作答。"
                            )
                        else:
                            combined_prompt = (
                                f"{safety_instruction}\n"
                                f"<vision_result>\n{desc}\n</vision_result>\n\n"
                                f"请分析并解释图片内容。"
                            )

                        try:
                            if memorize:
                                agent.memory.remember(
                                    content=desc,
                                    tag=f"image:{image_path.split('/')[-1]}"
                                )
                        except Exception:
                            pass

                        result = agent.chat(
                            combined_prompt, session_id, user_id,
                            response_style, image_path=image_path,
                            original_user_prompt=prompt
                        )

                        fallback_reply = (
                            "这是系统刚刚识别出的图片内容：\n"
                            f"{desc.strip()}\n"
                            "(由视觉识别直接生成)"
                        )

                        if isinstance(result, dict):
                            reply_text = result.get('reply', '')
                            if _looks_like_time_reply(reply_text):
                                result['reply'] = fallback_reply
                        elif isinstance(result, str):
                            if _looks_like_time_reply(result):
                                result = fallback_reply
                    else:
                        err = vision_result.get('error', '未知错误')
                        logger.error(f"❌ 图片识别失败: {err}")
                        # 降级处理：调用 agent.chat 确保用户消息被保存
                        result = agent.chat(
                            f"{prompt}\n[系统提示：用户上传了图片，但识别失败: {err}]",
                            session_id, user_id, response_style,
                            image_path=image_path,
                            original_user_prompt=prompt
                        )
                except Exception as e:
                    logger.error(f"❌ 图片处理出错: {str(e)}", exc_info=True)
                    # 降级处理：调用 agent.chat 确保用户消息被保存
                    result = agent.chat(
                        f"{prompt}\n[系统提示：图片处理出错: {str(e)}]",
                        session_id, user_id, response_style,
                        image_path=image_path,
                        original_user_prompt=prompt
                    )
            except Exception as e:
                logger.error(f"❌ VisionTool导入或初始化失败: {str(e)}", exc_info=True)
                # 降级处理：调用 agent.chat 确保用户消息被保存
                result = agent.chat(
                    f"{prompt}\n[系统提示：图片工具初始化失败: {str(e)}]",
                    session_id, user_id, response_style,
                    image_path=image_path,
                    original_user_prompt=prompt
                )
        else:
            # 常规对话
            logger.info(f"🔄 调用agent.chat - session_id: {session_id}")
            result = agent.chat(prompt, session_id, user_id, response_style)

        # 追问分析（异步重要性不高，这里保持与同步一致）
        try:
            actual_session_id = (
                result.get('session_id')
                if isinstance(result, dict) else session_id
            )
            if actual_session_id:
                try:
                    qa.analyze_conversation(actual_session_id, user_id)
                except Exception:
                    pass
        except Exception:
            pass

        reply = (
            result.get('reply') if isinstance(result, dict)
            else str(result)
        )

        # 🔥 关键修复: 在流式输出前检测并替换时间回复
        if image_path:
            logger.info("🔍流式检测reply是否像时间: %s, 前100字: %s",
                        _looks_like_time_reply(reply), reply[:100])
            if _looks_like_time_reply(reply):
                # 从vision_result中提取描述作为fallback
                try:
                    desc_start = reply.find('<vision_result>')
                    desc_end = reply.find('</vision_result>')
                    if desc_start != -1 and desc_end != -1:
                        desc = reply[desc_start+15:desc_end].strip()
                        if desc and "我通过视觉能力识别到的图片内容" in desc:
                            desc = desc.split(
                                "我通过视觉能力识别到的图片内容：", 1)[-1].strip()
                        fallback_reply = (
                            "这是系统刚刚识别出的图片内容：\n"
                            f"{desc}\n"
                            "(由视觉识别直接生成)"
                        )
                        logger.warning("⚠️ 流式接口触发fallback替换!")
                        reply = fallback_reply
                        if isinstance(result, dict):
                            result['reply'] = fallback_reply
                except Exception as e:
                    logger.error(f"提取vision描述失败: {e}")

        # 切片流式输出
        chunk_size = 120
        idx = 0
        while idx < len(reply):
            part = reply[idx: idx + chunk_size]
            idx += chunk_size
            payload = {"type": "delta", "data": part}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # 完成事件，带上元信息
        end_payload = {
            "type": "end",
            "session_id": (
                result.get('session_id')
                if isinstance(result, dict) else session_id
            ),
            "user_message_id": (
                result.get('user_message_id')
                if isinstance(result, dict) else None
            ),
            "assistant_message_id": (
                result.get('assistant_message_id')
                if isinstance(result, dict) else None
            ),
            "image_path": (
                body.image_path if body and hasattr(
                    body, 'image_path') else None
            ),
        }
        yield f"data: {json.dumps(end_payload, ensure_ascii=False)}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream; charset=utf-8"
    }
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=headers
    )


@router.get("/sessions")
def get_sessions(
    limit: Optional[int] = None,
    all_sessions: bool = False,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """获取用户的对话会话列表(使用认证用户)"""
    effective_limit = None if all_sessions else limit
    logger.info(
        f"📋 获取会话列表 - user_id: {current_user}, limit: {effective_limit}")
    sessions = agent.conversation.get_recent_sessions(
        current_user, effective_limit
    )
    return {"sessions": sessions}


@router.get("/debug/session/{session_id}")
def debug_session(session_id: str):
    """调试:检查特定会话的详细信息"""
    from db_setup import Session as DBSession, Conversation
    session = DBSession()
    try:
        conv = session.query(Conversation).filter(
            Conversation.session_id == session_id
        ).first()
        if conv:
            return {
                "found": True,
                "session_id": conv.session_id,
                "title": conv.title,
                "user_id": conv.user_id,
                "created_at": str(conv.created_at),
                "updated_at": str(conv.updated_at),
                "pinned": getattr(conv, 'pinned', False)
            }
        else:
            return {"found": False}
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


@router.get("/debug/count_by_user")
def debug_count_by_user():
    """调试:统计各user_id的会话数"""
    from db_setup import Session as DBSession, Conversation
    from sqlalchemy import func
    session = DBSession()
    try:
        counts = session.query(
            Conversation.user_id,
            func.count(Conversation.session_id).label('count')
        ).group_by(Conversation.user_id).all()
        return {"user_counts": [{"user_id": u, "count": c} for u, c in counts]}
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


@router.get("/admin/user_sessions_stats")
def get_user_sessions_stats():
    """管理员接口:查看所有user_id的会话统计"""
    from db_setup import SessionLocal, Conversation
    from sqlalchemy import func
    session = SessionLocal()
    try:
        # 按user_id统计会话数量
        stats = session.query(
            Conversation.user_id,
            func.count(Conversation.id).label('count')
        ).group_by(Conversation.user_id).all()

        result = [
            {"user_id": user_id, "count": count}
            for user_id, count in stats
        ]
        return {"stats": result, "total_users": len(result)}
    finally:
        session.close()


@router.post("/admin/migrate_user_sessions")
def migrate_user_sessions(
    from_user: str = "default_user",
    to_user: str = "admin"
):
    """管理员接口:将会话从一个用户迁移到另一个用户"""
    from db_setup import SessionLocal, Conversation
    from sqlalchemy import text
    session = SessionLocal()
    try:
        # 统计需要迁移的数量
        count = session.query(Conversation).filter(
            Conversation.user_id == from_user
        ).count()

        if count == 0:
            return {"migrated": 0, "message": "无需迁移"}

        # 使用原生SQL更新,避免触发updated_at自动更新
        session.execute(
            text("UPDATE conversations SET user_id = :to_user "
                 "WHERE user_id = :from_user"),
            {"to_user": to_user, "from_user": from_user}
        )

        session.commit()
        return {
            "migrated": count,
            "message": f"成功迁移 {count} 条会话从 {from_user} 到 {to_user}"
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e), "migrated": 0}
    finally:
        session.close()


@router.post("/admin/migrate_all_to_current")
def migrate_all_sessions_to_current(
    current_user: str = Depends(get_current_user)
):
    """管理员接口:将所有非当前用户的会话迁移到当前登录用户"""
    from db_setup import SessionLocal, Conversation
    from sqlalchemy import text
    session = SessionLocal()
    try:
        # 统计需要迁移的数量
        count = session.query(Conversation).filter(
            Conversation.user_id != current_user
        ).count()

        if count == 0:
            return {"migrated": 0, "message": "无需迁移"}

        # 使用原生SQL更新,避免触发updated_at自动更新
        session.execute(
            text("UPDATE conversations SET user_id = :current_user "
                 "WHERE user_id != :current_user"),
            {"current_user": current_user}
        )

        session.commit()
        return {
            "migrated": count,
            "message": f"成功迁移 {count} 条会话到当前用户 {current_user}"
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e), "migrated": 0}
    finally:
        session.close()


@router.post("/admin/fix_session_timestamps")
def fix_session_timestamps():
    """管理员接口:修复会话时间戳(将created_at复制到updated_at)"""
    from db_setup import SessionLocal
    from sqlalchemy import text
    session = SessionLocal()
    try:
        # 将所有会话的updated_at重置为created_at
        result = session.execute(
            text("UPDATE conversations SET updated_at = created_at")
        )
        session.commit()
        return {
            "fixed": result.rowcount,
            "message": f"成功修复 {result.rowcount} 条会话的时间戳"
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e), "fixed": 0}
    finally:
        session.close()


@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    limit: int = 200,
    agent: XiaoLeAgent = Depends(get_agent)
):
    """获取会话详情"""
    stats = agent.conversation.get_session_stats(session_id)
    history = agent.conversation.get_history(session_id, limit=limit)

    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": stats["session_id"],
        "title": stats["title"],
        "message_count": stats["message_count"],
        "created_at": stats["created_at"],
        "updated_at": stats["updated_at"],
        "messages": history
    }


@router.patch("/chat/sessions/{session_id}")
def update_session(
    session_id: str,
    update_data: Dict[str, Any],
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """更新会话信息"""
    try:
        # 验证会话所有权
        from db_setup import SessionLocal, Conversation
        db = SessionLocal()
        try:
            conv = db.query(Conversation).filter(
                Conversation.session_id == session_id,
                Conversation.user_id == current_user
            ).first()

            if not conv:
                raise HTTPException(status_code=404, detail="会话不存在或无权访问")
        finally:
            db.close()

        if "title" in update_data:
            agent.conversation.update_session_title(
                session_id, update_data["title"])

        if "pinned" in update_data:
            agent.conversation.update_session_pinned(
                session_id, update_data["pinned"])

        return {"message": "Session updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """删除会话"""
    user_id = current_user
    # 验证会话所有权
    from db_setup import SessionLocal, Conversation
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id
        ).first()
        if not conv:
            raise HTTPException(status_code=403, detail="无权删除此会话")
    finally:
        db.close()

    agent.conversation.delete_session(session_id)
    return {"message": "Session deleted"}


@router.delete("/chat/sessions/{session_id}")
def delete_session_api(
    session_id: str,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """删除会话"""
    user_id = current_user
    # 验证会话所有权
    from db_setup import SessionLocal, Conversation
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(
            Conversation.session_id == session_id,
            Conversation.user_id == user_id
        ).first()
        if not conv:
            raise HTTPException(status_code=403, detail="无权删除此会话")
    finally:
        db.close()

    agent.conversation.delete_session(session_id)
    return {"message": "Session deleted"}


@router.delete("/messages/{message_id}")
def delete_message_api(
    message_id: int,
    current_user: str = Depends(get_current_user),
    agent: XiaoLeAgent = Depends(get_agent)
):
    """删除消息及其后续消息"""
    user_id = current_user
    # 验证消息所有权
    from db_setup import SessionLocal, Message, Conversation
    db = SessionLocal()
    try:
        msg = db.query(Message).filter(Message.id == message_id).first()
        if not msg:
            raise HTTPException(status_code=404, detail="消息不存在")

        conv = db.query(Conversation).filter(
            Conversation.session_id == msg.session_id,
            Conversation.user_id == user_id
        ).first()
        if not conv:
            raise HTTPException(status_code=403, detail="无权删除此消息")
    finally:
        db.close()

    success = agent.conversation.delete_message_and_following(message_id)
    if success:
        return {"success": True, "message": "Messages deleted"}
    else:
        raise HTTPException(
            status_code=404,
            detail="Message not found or delete failed"
        )
