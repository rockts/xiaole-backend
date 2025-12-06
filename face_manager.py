try:
    import numpy as np
except ImportError:
    np = None

from sqlalchemy.orm import Session
from backend.db_setup import SessionLocal, FaceEncoding
import logging
import os

logger = logging.getLogger(__name__)


class FaceManager:
    def __init__(self):
        # We should create a new session per request or manage it better.
        # But for now, let's keep it simple but safe.
        pass

    def get_db(self):
        return SessionLocal()

    def health_check(self, user_id: str = "default_user"):
        """检查人脸库健康状态"""
        db = self.get_db()
        try:
            faces = db.query(FaceEncoding).filter(
                FaceEncoding.user_id == user_id
            ).all()

            issues = []
            for face in faces:
                # 检查是否有编码
                if not face.encoding:
                    issues.append(f"'{face.name}' 缺少人脸编码")
                # 检查图片路径是否存在
                if face.image_path and not os.path.exists(face.image_path):
                    issues.append(f"'{face.name}' 的图片文件不存在: {face.image_path}")

            return {
                "success": True,
                "total_faces": len(faces),
                "registered_people": list(set(f.name for f in faces)),
                "issues": issues,
                "healthy": len(issues) == 0
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def register_face(
        self, image_path: str, name: str, user_id: str = "default_user"
    ):
        """
        Register a face.
        Returns: dict with success, result/error
        """
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found: {image_path}"
            }

        db = self.get_db()
        try:
            if np is None:
                return {
                    "success": False,
                    "error": "numpy is not installed, cannot register face"
                }
            import face_recognition
            # Load image
            image = face_recognition.load_image_file(image_path)

            # Detect faces
            face_locations = face_recognition.face_locations(image)
            if len(face_locations) == 0:
                return {
                    "success": False,
                    "error": "No face detected in the image"
                }
            if len(face_locations) > 1:
                return {
                    "success": False,
                    "error": (
                        "Multiple faces detected. Please upload an image "
                        "with a single face."
                    )
                }

            # Extract encoding
            face_encodings = face_recognition.face_encodings(
                image, face_locations)
            if len(face_encodings) == 0:
                return {
                    "success": False,
                    "error": "Could not extract face encoding"
                }

            # Convert numpy array to list for DB storage
            encoding = face_encodings[0].tolist()

            # Save to DB
            new_face = FaceEncoding(
                user_id=user_id,
                name=name,
                encoding=encoding,
                image_path=image_path
            )

            db.add(new_face)
            db.commit()

            return {
                "success": True,
                "result": f"Face registered successfully for {name}"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error registering face: {e}")
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def get_known_faces(self, user_id: str = "default_user"):
        """
        Get known faces.
        Returns: (encodings, names)
        """
        if np is None:
            return [], []

        db = self.get_db()
        try:
            faces = db.query(FaceEncoding).filter(
                FaceEncoding.user_id == user_id
            ).all()
            encodings = []
            names = []
            for face in faces:
                if face.encoding:
                    encodings.append(np.array(face.encoding))
                    names.append(face.name)
            return encodings, names
        finally:
            db.close()

    def recognize_faces(self, image_path: str, user_id: str = "default_user"):
        """
        Recognize faces in an image.
        Returns: dict with success, identified_people, face_count, faces
        """
        if not os.path.exists(image_path):
            return {
                "success": False,
                "error": f"Image file not found: {image_path}"
            }

        try:
            if np is None:
                return {
                    "success": False,
                    "error": "numpy is not installed"
                }

            known_encodings, known_names = self.get_known_faces(user_id)

            import face_recognition
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)

            if not face_locations:
                return {
                    "success": True,
                    "identified_people": [],
                    "face_count": 0,
                    "faces": []
                }

            face_encodings = face_recognition.face_encodings(
                image, face_locations)
            found_names = []
            faces_details = []

            if not known_encodings:
                # No known faces, all are unknown
                found_names = ["未知人物"] * len(face_locations)
                faces_details = [
                    {
                        "name": "未知人物",
                        "matched": False,
                        "best_distance": None,
                        "confidence": 0.0
                    }
                    for _ in face_locations
                ]
            else:
                # thresholds - 提高阈值以减少误识别
                # face_recognition.compare_faces default tolerance=0.6
                try:
                    match_threshold = float(
                        os.getenv("FACE_MATCH_THRESHOLD", "0.45")
                    )
                except Exception:
                    match_threshold = 0.45

                for face_encoding in face_encodings:
                    name = "未知人物"

                    face_distances = face_recognition.face_distance(
                        known_encodings, face_encoding
                    )
                    best_distance = None
                    best_match_index = None
                    if len(face_distances) > 0:
                        best_match_index = int(np.argmin(face_distances))
                        best_distance = float(face_distances[best_match_index])

                    matched = False
                    if (
                        best_distance is not None and
                        best_distance <= match_threshold
                    ):
                        matched = True
                        name = known_names[best_match_index]

                    # heuristic confidence from distance
                    confidence = 0.0
                    if best_distance is not None:
                        # Map [0.3, 0.6] -> [1.0, 0.0]
                        low, high = 0.3, 0.6
                        if best_distance <= low:
                            confidence = 1.0
                        elif best_distance >= high:
                            confidence = 0.0
                        else:
                            confidence = (high - best_distance) / (high - low)

                    found_names.append(name)
                    faces_details.append({
                        "name": name,
                        "matched": matched,
                        "best_distance": best_distance,
                        "confidence": round(confidence, 3)
                    })

            return {
                "success": True,
                "identified_people": found_names,
                "face_count": len(face_locations),
                "faces": faces_details
            }

        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            return {"success": False, "error": str(e)}
