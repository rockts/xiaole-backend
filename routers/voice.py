from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from tools.baidu_voice_tool import baidu_voice_tool
import base64
from backend.logger import logger

router = APIRouter(
    prefix="/voice",
    tags=["voice"]
)


class TTSRequest(BaseModel):
    text: str
    person: int = 0
    speed: int = 5
    pitch: int = 5
    volume: int = 5
    audio_format: str = "mp3"  # mp3|wav|pcm


@router.post("/recognize")
async def voice_recognize(file: UploadFile = File(...)):
    """
    语音识别接口（使用百度API）
    """
    try:
        if not baidu_voice_tool.is_enabled():
            raise HTTPException(status_code=503, detail="百度语音服务未配置，请设置环境变量")

        audio_data = await file.read()

        filename = file.filename.lower() if file.filename else ""
        if filename.endswith('.wav'):
            format_type = 'wav'
        elif filename.endswith('.pcm'):
            format_type = 'pcm'
        elif filename.endswith('.amr'):
            format_type = 'amr'
        elif filename.endswith('.m4a'):
            format_type = 'm4a'
        else:
            format_type = 'wav'

        result = await baidu_voice_tool.recognize(
            audio_data,
            format=format_type,
            rate=16000
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音识别失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


@router.get("/status")
def voice_status(detailed: bool = False):
    """检查语音服务状态"""
    return baidu_voice_tool.get_status(detailed)


@router.post("/synthesize")
async def voice_synthesize(req: TTSRequest):
    """文本转语音（百度TTS）"""
    try:
        if not baidu_voice_tool.is_enabled():
            raise HTTPException(status_code=503, detail="百度语音服务未配置，请设置环境变量")

        audio_bytes = await baidu_voice_tool.synthesize(
            text=req.text,
            person=req.person,
            speed=req.speed,
            pitch=req.pitch,
            volume=req.volume,
            audio_format=req.audio_format,
        )

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="语音合成失败")

        mime = "audio/mpeg"
        fmt = (req.audio_format or "mp3").lower()
        if fmt == "wav":
            mime = "audio/wav"
        elif fmt == "pcm":
            mime = "audio/x-pcm"

        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "success": True,
            "audio_base64": b64,
            "mime": mime,
            "format": fmt,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"语音合成异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"语音合成异常: {str(e)}")
