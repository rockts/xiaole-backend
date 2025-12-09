"""
百度人脸识别工具
使用百度 AI 开放平台的人脸识别 API 替代本地 face_recognition 库
"""
import os
import base64
import requests
import logging
import json
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class BaiduFaceClient:
    """百度人脸识别 API 客户端"""

    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    DETECT_URL = "https://aip.baidubce.com/rest/2.0/face/v3/detect"
    SEARCH_URL = "https://aip.baidubce.com/rest/2.0/face/v3/search"
    ADD_USER_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/add"
    DELETE_USER_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/delete"
    GET_USER_LIST_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/group/getusers"
    GROUP_ADD_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/group/add"

    def __init__(self):
        self.app_id = os.getenv("BAIDU_FACE_APP_ID")
        self.api_key = os.getenv("BAIDU_FACE_API_KEY")
        self.secret_key = os.getenv("BAIDU_FACE_SECRET_KEY")
        self._access_token = None
        self._token_expires_at = 0
        self.group_id = "xiaole_faces"  # 人脸库分组ID

    def _is_configured(self) -> bool:
        """检查是否配置了百度人脸识别 API"""
        return all([self.app_id, self.api_key, self.secret_key])

    def _get_access_token(self) -> Optional[str]:
        """获取百度 API access_token"""
        if not self._is_configured():
            logger.warning("百度人脸识别 API 未配置")
            return None

        # 检查 token 是否过期
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        try:
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key
            }
            response = requests.post(self.TOKEN_URL, params=params, timeout=10)
            result = response.json()

            if "access_token" in result:
                self._access_token = result["access_token"]
                # Token 有效期通常是 30 天，这里设置 29 天后过期
                self._token_expires_at = time.time() + result.get("expires_in", 2592000) - 86400
                logger.info("✅ 百度人脸识别 access_token 获取成功")
                return self._access_token
            else:
                logger.error("获取 access_token 失败: %s", result)
                return None
        except Exception as e:
            logger.error("获取 access_token 异常: %s", e)
            return None

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """将图片转为 base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error("读取图片失败: %s", e)
            return None

    def ensure_group_exists(self) -> bool:
        """确保人脸库分组存在"""
        token = self._get_access_token()
        if not token:
            return False

        try:
            params = {"access_token": token}
            data = {"group_id": self.group_id}
            response = requests.post(
                self.GROUP_ADD_URL,
                params=params,
                data=data,
                timeout=10
            )
            result = response.json()
            # error_code 为 0 或 223101（分组已存在）都算成功
            if result.get("error_code") in [0, 223101]:
                return True
            logger.warning("创建人脸库分组失败: %s", result)
            return False
        except Exception as e:
            logger.error("创建人脸库分组异常: %s", e)
            return False

    def detect_faces(self, image_path: str) -> Dict[str, Any]:
        """
        检测图片中的人脸
        返回: {success, face_count, faces: [{location, quality, ...}]}
        """
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取 access_token 失败"}

        image_base64 = self._image_to_base64(image_path)
        if not image_base64:
            return {"success": False, "error": f"无法读取图片: {image_path}"}

        try:
            params = {"access_token": token}
            data = {
                "image": image_base64,
                "image_type": "BASE64",
                "face_field": "age,beauty,expression,face_shape,gender,glasses,emotion",
                "max_face_num": 10
            }

            response = requests.post(
                self.DETECT_URL,
                params=params,
                data=data,
                timeout=15
            )
            result = response.json()

            if result.get("error_code") == 0:
                face_list = result.get("result", {}).get("face_list", [])
                return {
                    "success": True,
                    "face_count": len(face_list),
                    "faces": face_list
                }
            elif result.get("error_code") == 222202:
                # 未检测到人脸
                return {"success": True, "face_count": 0, "faces": []}
            else:
                return {
                    "success": False,
                    "error": f"百度 API 错误: {result.get('error_msg', '未知错误')}"
                }

        except Exception as e:
            logger.error("人脸检测异常: %s", e)
            return {"success": False, "error": str(e)}

    def register_face(
        self,
        image_path: str,
        person_name: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """
        注册人脸到百度人脸库
        person_name: 人名（用于显示）
        user_id: 用户ID（用于唯一标识，默认使用 person_name）
        """
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        # 确保分组存在
        if not self.ensure_group_exists():
            return {"success": False, "error": "创建人脸库分组失败"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取 access_token 失败"}

        image_base64 = self._image_to_base64(image_path)
        if not image_base64:
            return {"success": False, "error": f"无法读取图片: {image_path}"}

        # 使用 person_name 作为 user_id（去除空格和特殊字符）
        if not user_id:
            user_id = person_name.replace(" ", "_").replace("-", "_")

        try:
            params = {"access_token": token}
            data = {
                "image": image_base64,
                "image_type": "BASE64",
                "group_id": self.group_id,
                "user_id": user_id,
                "user_info": json.dumps({"name": person_name}, ensure_ascii=False),
                "quality_control": "NORMAL",
                "liveness_control": "NONE",
                "action_type": "REPLACE"  # 如果用户已存在则替换
            }

            response = requests.post(
                self.ADD_USER_URL,
                params=params,
                data=data,
                timeout=30
            )
            result = response.json()

            if result.get("error_code") == 0:
                logger.info("✅ 人脸注册成功: %s", person_name)
                return {
                    "success": True,
                    "result": f"已成功注册 {person_name} 的人脸"
                }
            elif result.get("error_code") == 222202:
                return {"success": False, "error": "图片中未检测到人脸"}
            elif result.get("error_code") == 222203:
                return {"success": False, "error": "检测到多张人脸，请上传单人照片"}
            else:
                return {
                    "success": False,
                    "error": f"注册失败: {result.get('error_msg', '未知错误')}"
                }

        except Exception as e:
            logger.error("人脸注册异常: %s", e)
            return {"success": False, "error": str(e)}

    def search_face(
        self,
        image_path: str,
        face_token: str = None
    ) -> Dict[str, Any]:
        """
        在人脸库中搜索匹配的人脸
        返回: {success, matched, person_name, confidence, ...}
        """
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取 access_token 失败"}

        image_base64 = self._image_to_base64(image_path)
        if not image_base64:
            return {"success": False, "error": f"无法读取图片: {image_path}"}

        try:
            params = {"access_token": token}
            data = {
                "image": image_base64,
                "image_type": "BASE64",
                "group_id_list": self.group_id,
                "quality_control": "NORMAL",
                "liveness_control": "NONE",
                "max_user_num": 3  # 返回最多3个匹配结果
            }

            response = requests.post(
                self.SEARCH_URL,
                params=params,
                data=data,
                timeout=15
            )
            result = response.json()

            if result.get("error_code") == 0:
                user_list = result.get("result", {}).get("user_list", [])
                if user_list:
                    best_match = user_list[0]
                    score = best_match.get("score", 0)
                    user_id = best_match.get("user_id", "")
                    user_info = best_match.get("user_info", "{}")

                    try:
                        info = json.loads(user_info) if user_info else {}
                        person_name = info.get("name", user_id)
                    except:
                        person_name = user_id

                    # 百度返回的 score 是 0-100，转换为 0-1 的置信度
                    confidence = score / 100.0

                    # 阈值判断（score >= 80 认为匹配）
                    matched = score >= 80

                    return {
                        "success": True,
                        "matched": matched,
                        "person_name": person_name if matched else "未知人物",
                        "confidence": confidence,
                        "score": score,
                        "all_matches": [
                            {
                                "user_id": u.get("user_id"),
                                "score": u.get("score"),
                                "confidence": u.get("score", 0) / 100.0
                            }
                            for u in user_list
                        ]
                    }
                else:
                    return {
                        "success": True,
                        "matched": False,
                        "person_name": "未知人物",
                        "confidence": 0,
                        "score": 0
                    }
            elif result.get("error_code") == 222202:
                return {
                    "success": True,
                    "matched": False,
                    "person_name": "未知人物",
                    "confidence": 0,
                    "error": "未检测到人脸"
                }
            elif result.get("error_code") == 223105:
                # 人脸库为空
                return {
                    "success": True,
                    "matched": False,
                    "person_name": "未知人物",
                    "confidence": 0,
                    "error": "人脸库为空"
                }
            else:
                return {
                    "success": False,
                    "error": f"搜索失败: {result.get('error_msg', '未知错误')}"
                }

        except Exception as e:
            logger.error("人脸搜索异常: %s", e)
            return {"success": False, "error": str(e)}

    def recognize_faces(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """
        识别图片中的所有人脸
        兼容 FaceManager.recognize_faces 的返回格式
        """
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        # 先检测人脸
        detect_result = self.detect_faces(image_path)
        if not detect_result.get("success"):
            return detect_result

        face_count = detect_result.get("face_count", 0)
        if face_count == 0:
            return {
                "success": True,
                "identified_people": [],
                "face_count": 0,
                "faces": []
            }

        # 搜索匹配
        search_result = self.search_face(image_path)
        if not search_result.get("success"):
            # 搜索失败时，仍然返回检测结果
            return {
                "success": True,
                "identified_people": ["未知人物"] * face_count,
                "face_count": face_count,
                "faces": [
                    {
                        "name": "未知人物",
                        "matched": False,
                        "confidence": 0.0
                    }
                    for _ in range(face_count)
                ]
            }

        # 构建返回结果
        identified_people = []
        faces_details = []

        if search_result.get("matched"):
            person_name = search_result.get("person_name", "未知人物")
            confidence = search_result.get("confidence", 0)
            identified_people.append(person_name)
            faces_details.append({
                "name": person_name,
                "matched": True,
                "confidence": confidence,
                "score": search_result.get("score", 0)
            })
        else:
            identified_people.append("未知人物")
            faces_details.append({
                "name": "未知人物",
                "matched": False,
                "confidence": search_result.get("confidence", 0),
                "score": search_result.get("score", 0)
            })

        # 如果检测到多张人脸，其他的标记为未知
        for _ in range(1, face_count):
            identified_people.append("未知人物")
            faces_details.append({
                "name": "未知人物",
                "matched": False,
                "confidence": 0.0
            })

        return {
            "success": True,
            "identified_people": identified_people,
            "face_count": face_count,
            "faces": faces_details
        }

    def get_registered_users(self) -> Dict[str, Any]:
        """获取已注册的用户列表"""
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取 access_token 失败"}

        try:
            params = {"access_token": token}
            data = {
                "group_id": self.group_id,
                "start": 0,
                "length": 100
            }

            response = requests.post(
                self.GET_USER_LIST_URL,
                params=params,
                data=data,
                timeout=10
            )
            result = response.json()

            if result.get("error_code") == 0:
                user_list = result.get("result", {}).get("user_id_list", [])
                return {
                    "success": True,
                    "users": user_list,
                    "count": len(user_list)
                }
            elif result.get("error_code") == 223101:
                # 分组不存在
                return {"success": True, "users": [], "count": 0}
            else:
                return {
                    "success": False,
                    "error": f"获取用户列表失败: {result.get('error_msg')}"
                }

        except Exception as e:
            logger.error("获取用户列表异常: %s", e)
            return {"success": False, "error": str(e)}

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """删除用户"""
        if not self._is_configured():
            return {"success": False, "error": "百度人脸识别 API 未配置"}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "获取 access_token 失败"}

        try:
            params = {"access_token": token}
            data = {
                "group_id": self.group_id,
                "user_id": user_id
            }

            response = requests.post(
                self.DELETE_USER_URL,
                params=params,
                data=data,
                timeout=10
            )
            result = response.json()

            if result.get("error_code") == 0:
                return {"success": True, "result": f"已删除用户 {user_id}"}
            else:
                return {
                    "success": False,
                    "error": f"删除失败: {result.get('error_msg')}"
                }

        except Exception as e:
            logger.error("删除用户异常: %s", e)
            return {"success": False, "error": str(e)}


# 全局实例
baidu_face_client = BaiduFaceClient()
