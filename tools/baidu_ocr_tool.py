"""
百度文字识别工具 (OCR)
支持通用文字识别、手写文字识别
"""
import os
from typing import Optional, Dict, Any, List
from aip import AipOcr
from dotenv import load_dotenv

load_dotenv()


class BaiduOCRTool:
    """百度OCR工具类"""

    def __init__(self):
        """初始化百度OCR客户端"""
        self.app_id = os.getenv('BAIDU_APP_ID', '')
        self.api_key = os.getenv('BAIDU_API_KEY', '')
        self.secret_key = os.getenv('BAIDU_SECRET_KEY', '')

        self.client: Optional[AipOcr] = None
        if self.app_id and self.api_key and self.secret_key:
            self.client = AipOcr(self.app_id, self.api_key, self.secret_key)
            print("✅ 百度OCR服务初始化成功")
        else:
            print("⚠️  百度OCR服务未配置 (复用语音服务的KEY)")

    def is_enabled(self) -> bool:
        return self.client is not None

    def recognize_handwriting(self, image_data: bytes) -> Dict[str, Any]:
        """
        手写文字识别
        """
        if not self.is_enabled():
            return {"success": False, "error": "OCR服务未配置"}

        try:
            # 调用百度手写识别接口
            options = {"recognize_granularity": "big"}
            result = self.client.handwriting(image_data, options)

            if "words_result" in result:
                words = [w["words"] for w in result["words_result"]]
                text = "\n".join(words)
                return {"success": True, "text": text}
            else:
                return {"success": False, "error": result.get("error_msg", "未知错误")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def recognize_general(self, image_data: bytes) -> Dict[str, Any]:
        """
        通用文字识别（高精度版）
        """
        if not self.is_enabled():
            return {"success": False, "error": "OCR服务未配置"}

        try:
            options = {"detect_direction": "true"}
            result = self.client.basicAccurate(image_data, options)

            if "words_result" in result:
                words = [w["words"] for w in result["words_result"]]
                text = "\n".join(words)
                return {"success": True, "text": text}
            else:
                return {"success": False, "error": result.get("error_msg", "未知错误")}

        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局实例
baidu_ocr_tool = BaiduOCRTool()
