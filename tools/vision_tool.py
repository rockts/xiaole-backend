import os
import logging
import base64
import requests
import json
from typing import Dict, Any, List, Optional
from backend.tool_manager import Tool, ToolParameter
from backend.face_manager import FaceManager
from backend.config import UPLOADS_DIR

logger = logging.getLogger(__name__)


class VisionTool(Tool):
    def __init__(self):
        super().__init__()
        self.name = "vision_analysis"
        self.description = "Analyze images to identify people using face recognition."
        self.category = "vision"
        self.parameters = [
            ToolParameter(
                name="image_path",
                param_type="string",
                description="The path to the image file to analyze.",
                required=True
            )
        ]
        self.qwen_key = os.getenv("QWEN_API_KEY")
        self.claude_key = os.getenv("CLAUDE_API_KEY")
        self.face_manager = FaceManager()

    def _resolve_path(self, image_path: str) -> Optional[str]:
        """Resolve image path relative to backend or project root"""
        # Handle /uploads/ prefix mapping
        if image_path.startswith("/uploads/") or image_path.startswith("uploads/"):
            # Remove prefix
            clean_path = image_path.lstrip("/").replace("uploads/", "", 1)
            # Map to UPLOADS_DIR
            potential_path = os.path.join(UPLOADS_DIR, clean_path)
            if os.path.exists(potential_path):
                return potential_path

        if os.path.exists(image_path):
            return image_path

        # Try relative to backend root
        backend_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        potential_path = os.path.join(backend_root, image_path)
        if os.path.exists(potential_path):
            return potential_path

        # Try relative to project root
        project_root = os.path.dirname(backend_root)
        potential_path = os.path.join(project_root, image_path)
        if os.path.exists(potential_path):
            return potential_path

        # Try removing leading slash if present
        if image_path.startswith('/'):
            return self._resolve_path(image_path[1:])

        return None

    def analyze_image(self, image_path: str, prompt: str = None, prefer_model: str = "auto") -> Dict[str, Any]:
        """
        Analyze image content using hybrid approach:
        1. Use FaceManager to identify known people
        2. Use Vision LLM (Qwen-VL/Claude) for general scene description
        """
        try:
            if not prompt:
                prompt = "请详细描述这张图片的内容。"

            full_path = self._resolve_path(image_path)
            if not full_path:
                return {"success": False, "error": f"Image file not found: {image_path}"}

            # Step 1: Face Recognition using FaceManager
            face_info = ""
            face_details: List[Dict[str, Any]] = []
            try:
                # Use FaceManager to recognize faces
                recognition_result = self.face_manager.recognize_faces(
                    full_path)

                if recognition_result['success']:
                    identified_people = recognition_result['identified_people']
                    face_count = recognition_result['face_count']
                    face_details = recognition_result.get('faces', [])

                    # threshold for announcing identities - 提高到0.75
                    try:
                        announce_threshold = float(
                            os.getenv("FACE_ANNOUNCE_THRESHOLD", "0.75"))
                    except Exception:
                        announce_threshold = 0.75

                    # Filter out unknown people
                    known_people = [
                        p for p in identified_people if p != "未知人物"]

                    if known_people:
                        # If low confidence, ask for confirmation
                        low_conf = any(
                            (d.get('name') in known_people and (
                                d.get('confidence') or 0) < announce_threshold)
                            for d in face_details
                        )
                        if low_conf:
                            # 低置信度时明确要求确认，不直接断言身份
                            conf_vals = [
                                f"{d.get('name')}({d.get('confidence', 0):.2f})"
                                for d in face_details
                                if d.get('name') in known_people
                            ]
                            face_info = (
                                f"【人脸识别】检测到可能的匹配：{', '.join(conf_vals)}。"
                                f"置信度较低，**请确认身份后再告诉我这是谁**，避免记录错误。\n"
                            )
                        else:
                            face_info = f"【人脸识别结果】图中发现了以下熟人：{', '.join(known_people)}。\n"
                    elif face_count > 0:
                        face_info = f"【人脸识别结果】图中发现了 {face_count} 个人，但未识别出具体身份。\n"
                    else:
                        # No faces found
                        pass
                else:
                    logger.warning(
                        f"Face recognition warning: {recognition_result.get('error')}")
                    face_info = "【人脸识别】人脸检测过程中出现错误，跳过此步骤。\n"

            except Exception as e:
                logger.error(f"Face recognition failed: {e}")
                face_info = "【人脸识别】人脸检测过程中出现错误，跳过此步骤。\n"

            # Step 2: Vision LLM Analysis
            llm_result = {}
            # Dispatch based on model preference and availability
            if prefer_model == "qwen" or (prefer_model == "auto" and self.qwen_key):
                llm_result = self.analyze_with_qwen(full_path, prompt)
            elif prefer_model == "claude" or (prefer_model == "auto" and self.claude_key):
                llm_result = self.analyze_with_claude(full_path, prompt)
            else:
                llm_result = {
                    "success": False,
                    "error": "No suitable vision model configured. Please set QWEN_API_KEY or CLAUDE_API_KEY."
                }

            if not llm_result.get("success"):
                # 模型不可用时，仍返回人脸识别结果，描述为空
                llm_result = {"success": False,
                              "description": "", "model": "unavailable"}

            # Combine results
            final_description = face_info + "\n" + \
                llm_result.get("description", "")

            return {
                "success": True,
                "description": final_description.strip(),
                "model": llm_result.get("model", "unknown"),
                "face_info": face_info,
                "face_details": face_details
            }

        except Exception as e:
            logger.error(f"Analyze image failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def analyze_with_qwen(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Use Qwen-VL-Plus for image analysis"""
        try:
            if not self.qwen_key:
                return {"success": False, "error": "Qwen API key not configured"}

            # Encode image to base64
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')

            # Determine mime type
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/jpeg"
            if ext == ".png":
                mime_type = "image/png"
            elif ext == ".webp":
                mime_type = "image/webp"
            elif ext == ".gif":
                mime_type = "image/gif"

            data_uri = f"data:{mime_type};base64,{base64_image}"

            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.qwen_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "qwen-vl-plus",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": data_uri},
                                {"text": prompt}
                            ]
                        }
                    ]
                }
            }

            response = requests.post(
                url, headers=headers, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if "output" in result and "choices" in result["output"]:
                    content = result["output"]["choices"][0]["message"]["content"][0]["text"]
                    return {
                        "success": True,
                        "description": content,
                        "model": "qwen-vl-plus"
                    }
                else:
                    return {"success": False, "error": f"Qwen API format error: {result}"}
            else:
                return {"success": False, "error": f"Qwen API error: {response.status_code} - {response.text}"}

        except Exception as e:
            return {"success": False, "error": f"Qwen analysis failed: {str(e)}"}

    def analyze_with_claude(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Use Claude 3.5 Sonnet for image analysis"""
        try:
            if not self.claude_key:
                return {"success": False, "error": "Claude API key not configured"}

            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_key)

            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            ext = os.path.splitext(image_path)[1].lower().replace('.', '')
            if ext == 'jpg':
                ext = 'jpeg'
            media_type = f"image/{ext}"

            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ],
                    }
                ],
            )

            return {
                "success": True,
                "description": message.content[0].text,
                "model": "claude-3-5-sonnet"
            }

        except Exception as e:
            return {"success": False, "error": f"Claude analysis failed: {str(e)}"}

    async def execute(self, image_path: str, prompt: str = None, **kwargs) -> Dict[str, Any]:
        try:
            # Handle relative paths
            image_path = self._resolve_path(image_path) or image_path

            # Check if path exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}",
                    "result": None
                }

            logger.info(f"👁️ VisionTool analyzing: {image_path}")

            # Use the hybrid analysis method
            analysis_result = self.analyze_image(image_path, prompt=prompt)

            if not analysis_result.get("success"):
                return {
                    "success": False,
                    "error": analysis_result.get("error", "Unknown error during analysis"),
                    "result": None
                }

            return {
                "success": True,
                "result": {
                    "description": analysis_result.get("description", ""),
                    "face_info": analysis_result.get("face_info", ""),
                    "model": analysis_result.get("model", "unknown")
                }
            }

        except Exception as e:
            logger.error(f"VisionTool error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    def save_upload(self, file_data: bytes, filename: str) -> tuple[bool, str]:
        """Save uploaded image file"""
        try:
            # Determine upload directory
            # Try to find backend/uploads directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # tools/vision_tool.py -> tools/ -> root -> backend -> uploads

            project_root = os.path.dirname(current_dir)
            # 修改为 uploads/images 子目录
            uploads_dir = os.path.join(
                project_root, "backend", "uploads", "images")

            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir, exist_ok=True)

            # Generate safe filename
            import time
            timestamp = int(time.time())
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(uploads_dir, safe_filename)

            # Save file
            with open(file_path, "wb") as f:
                f.write(file_data)

            # Return relative path (for frontend access)
            # Frontend access /uploads/images/xxx -> Backend mount /uploads
            # -> backend/uploads/images/xxx
            return True, f"/uploads/images/{safe_filename}"

        except Exception as e:
            logger.error(f"Failed to save uploaded image: {e}")
            return False, str(e)


class RegisterFaceTool(Tool):
    def __init__(self):
        super().__init__()
        self.name = "register_face"
        self.description = "Register a new face for recognition. Use this when the user explicitly says 'This is [Name]' or wants to teach the AI a person's face."
        self.category = "vision"
        self.parameters = [
            ToolParameter(
                name="image_path",
                param_type="string",
                description="The path to the image file containing the face.",
                required=True
            ),
            ToolParameter(
                name="person_name",
                param_type="string",
                description="The name of the person to register.",
                required=True
            )
        ]
        self.face_manager = FaceManager()

    def _resolve_path(self, image_path: str) -> Optional[str]:
        """Resolve image path relative to backend or project root"""
        # Handle /uploads/ prefix mapping
        if image_path.startswith("/uploads/") or image_path.startswith("uploads/"):
            # Remove prefix
            clean_path = image_path.lstrip("/").replace("uploads/", "", 1)
            # Map to UPLOADS_DIR
            potential_path = os.path.join(UPLOADS_DIR, clean_path)
            if os.path.exists(potential_path):
                return potential_path

        if os.path.exists(image_path):
            return image_path

        # Try relative to backend root
        backend_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        potential_path = os.path.join(backend_root, image_path)
        if os.path.exists(potential_path):
            return potential_path

        # Try relative to project root
        project_root = os.path.dirname(backend_root)
        potential_path = os.path.join(project_root, image_path)
        if os.path.exists(potential_path):
            return potential_path

        # Try removing leading slash if present
        if image_path.startswith('/'):
            return self._resolve_path(image_path[1:])

        return None

    async def execute(self, image_path: str, person_name: str, **kwargs) -> Dict[str, Any]:
        try:
            full_path = self._resolve_path(image_path)
            if not full_path:
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }

            logger.info(
                f"👤 Registering face for '{person_name}' from {full_path}")

            # Use FaceManager to register face
            result = self.face_manager.register_face(full_path, person_name)

            return result

        except Exception as e:
            logger.error(f"RegisterFaceTool error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
