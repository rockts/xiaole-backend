from fastapi import APIRouter, Body, HTTPException
from face_manager import FaceManager
from db_setup import SessionLocal, FaceEncoding
import os

router = APIRouter(
    prefix="/faces",
    tags=["faces"]
)


@router.get("")
def list_faces():
    """列出所有已注册的人脸"""
    try:
        manager = FaceManager()
        encodings, names = manager.get_known_faces()

        face_counts = {}
        for name in names:
            face_counts[name] = face_counts.get(name, 0) + 1

        result = [
            {"name": name, "count": count}
            for name, count in face_counts.items()
        ]

        return {
            "success": True,
            "faces": result,
            "total_people": len(result),
            "total_encodings": len(names)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/{name}")
def delete_face(name: str):
    """删除指定人名下的所有面部数据"""
    try:
        db = SessionLocal()
        try:
            deleted_count = db.query(FaceEncoding).filter(
                FaceEncoding.name == name).delete()
            db.commit()

            return {
                "success": True,
                "message": f"已删除 '{name}' 的 {deleted_count} 条面部数据",
                "deleted_count": deleted_count
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/register")
def register_face(payload: dict = Body(...)):
    """注册一张人脸（用于前端确认后提交）

    Body: { image_path: '/uploads/images/xxx.jpg', person_name: '张三' }
    """
    try:
        image_path = payload.get('image_path')
        person_name = payload.get('person_name')
        if not image_path or not person_name:
            raise HTTPException(
                status_code=400,
                detail="image_path 与 person_name 必填"
            )

        # 将 /uploads/images/xxx.jpg 解析为后端真实文件路径
        # backend/uploads/images/xxx.jpg
        # 去掉可能的前导斜杠再拼接
        rel = image_path.lstrip('/')
        abs_path = os.path.join(
            os.path.dirname(__file__),  # backend/routers
            '..',  # backend
            rel.split('/', 1)[1] if '/' in rel else rel
        )
        abs_path = os.path.abspath(abs_path)

        manager = FaceManager()
        res = manager.register_face(abs_path, person_name)
        if not res.get('success'):
            raise HTTPException(
                status_code=400,
                detail=res.get('error', 'register failed')
            )

        return {"success": True, "message": res.get('result', 'ok')}

    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}
