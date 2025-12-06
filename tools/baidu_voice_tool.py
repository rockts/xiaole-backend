"""
百度语音识别工具
支持语音识别（ASR）和语音合成（TTS）
"""
import os
from typing import Optional, Dict, Any, cast

from aip import AipSpeech
from dotenv import load_dotenv


# 确保在模块加载时读取 .env（如果存在）
load_dotenv()


class BaiduVoiceTool:
    """百度语音识别工具类"""

    def __init__(self):
        """初始化百度语音客户端"""
        # 从环境变量读取配置
        self.app_id = os.getenv('BAIDU_APP_ID', '')
        self.api_key = os.getenv('BAIDU_API_KEY', '')
        self.secret_key = os.getenv('BAIDU_SECRET_KEY', '')
        # 语音客户端
        self.client: Optional[AipSpeech] = None
        if self.app_id and self.api_key and self.secret_key:
            self.client = AipSpeech(self.app_id, self.api_key, self.secret_key)
            print("✅ 百度语音服务初始化成功（已加载密钥）")
        else:
            print("⚠️  百度语音服务未配置，请设置环境变量：")
            print("   BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY")

    def is_enabled(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None

    @staticmethod
    def _mask(value: str, show: int = 4) -> str:
        """对敏感值做脱敏显示，仅显示末尾若干位"""
        if not value:
            return ""
        if len(value) <= show:
            return "*" * len(value)
        return ("*" * (len(value) - show)) + value[-show:]

    def get_status(self, detailed: bool = False) -> Dict[str, Any]:
        """
        获取服务状态

        Args:
            detailed: 是否返回详细（脱敏）信息

        Returns:
            dict: 状态信息
        """
        base = {
            "enabled": self.is_enabled(),
            "service": "百度语音识别",
            "provider": "Baidu AI",
        }

        if not detailed:
            return base

        return {
            **base,
            "configured": all([self.app_id, self.api_key, self.secret_key]),
            "has_app_id": bool(self.app_id),
            "has_api_key": bool(self.api_key),
            "has_secret_key": bool(self.secret_key),
            "app_id_masked": self._mask(self.app_id),
            "api_key_masked": self._mask(self.api_key),
            "secret_key_masked": self._mask(self.secret_key),
        }

    async def recognize(
        self,
        audio_data: bytes,
        format: str = 'wav',
        rate: int = 16000
    ) -> dict:
        """
        语音识别（ASR）

        Args:
            audio_data: 音频二进制数据
            format: 音频格式（wav/pcm/amr/m4a）
            rate: 采样率（8000/16000）

        Returns:
            {"success": True/False, "text": "识别结果", "error": "错误信息"}
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "百度语音服务未配置"
            }

        try:
            # 调用百度语音识别
            client = self.client
            if client is None:  # 再次保护（理论上前面已判断）
                return {"success": False, "error": "客户端未初始化"}

            print(f"🔍 开始语音识别: 格式={format}, 采样率={rate}, "
                  f"数据大小={len(audio_data)} bytes")

            result = client.asr(audio_data, format, rate, {
                'dev_pid': 1537,  # 1537=普通话(支持简单的英文识别)
                'cuid': 'xiaole-ai',
            })

            print(f"📥 百度API响应: {result}")

            # 检查结果类型
            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": f"API返回异常类型: {type(result)}"
                }

            if result.get('err_no') == 0:
                # 识别成功
                text = ''.join(result.get('result', []))
                print(f"✅ 识别成功: {text}")
                return {
                    "success": True,
                    "text": text
                }
            else:
                # 识别失败
                err_no = result.get('err_no')
                error_msg = result.get('err_msg', '未知错误')
                print(f"❌ 识别失败: err_no={err_no}, err_msg={error_msg}")
                return {
                    "success": False,
                    "error": f"识别失败 ({err_no}): {error_msg}",
                    "err_no": err_no
                }

        except KeyError as e:
            print(f"❌ KeyError: {str(e)}")
            print("   可能原因: API密钥错误或网络问题")
            return {
                "success": False,
                "error": f"API密钥错误或网络问题: {str(e)}"
            }
        except Exception as e:
            print(f"❌ 识别异常: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"识别异常: {str(e)}"
            }

    async def synthesize(
        self,
        text: str,
        person: int = 0,
        speed: int = 5,
        pitch: int = 5,
        volume: int = 5,
        audio_format: str = "mp3",
    ) -> Optional[bytes]:
        """
        语音合成（TTS）

        Args:
            text: 要合成的文本
            person: 发音人选择
                    0=度小美(女声,温柔)
                    1=度小宇(男声,温和)
                    3=度逍遥(男声,年轻)
                    4=度丫丫(女声,活泼)
                    注：高级音色(5,103,106等)需付费版本
            speed: 语速（0-15，默认5）
            pitch: 音调（0-15，默认5）
            volume: 音量（0-15，默认5）
            audio_format: 音频格式（mp3/pcm/wav）

        Returns:
            音频二进制数据，失败返回None
        """
        if not self.is_enabled():
            print("⚠️  百度语音服务未配置")
            return None

        try:
            client = self.client
            if client is None:
                print("⚠️  客户端未初始化，无法语音合成")
                return None

            # 映射音频格式到百度 aue 参数
            aue_map = {
                "mp3": 3,  # 默认
                "pcm": 4,  # 16k pcm
                "wav": 6,
            }
            aue = aue_map.get(audio_format.lower(), 3)

            result = client.synthesis(text, 'zh', 1, {
                'spd': speed,
                'pit': pitch,
                'vol': volume,
                'per': person,
                'aue': aue,
            })

            # 如果返回字典则是错误
            if isinstance(result, dict):
                error_msg = result.get('err_msg', '未知错误')
                print(f"❌ 语音合成失败: {error_msg}")
                return None

            # 返回的是音频数据
            return cast(bytes, result)

        except Exception as e:
            print(f"❌ 语音合成异常: {str(e)}")
            return None


# 创建全局实例
baidu_voice_tool = BaiduVoiceTool()
