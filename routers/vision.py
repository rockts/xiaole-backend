from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import Body
import os
import time
from backend.config import UPLOADS_DIR
import sys

# 允许导入项目根目录下的 tools 包
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 修正：需要添加项目根目录（backend的父目录），而不是backend目录
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.memory import MemoryManager  # noqa: E402
from tools.vision_tool import VisionTool  # noqa: E402

router = APIRouter(
    prefix="/vision",
    tags=["vision"]
)


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image for vision processing
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )

        # Ensure images directory exists
        images_dir = os.path.join(UPLOADS_DIR, "images")
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)

        # Generate unique filename
        import uuid
        ext = os.path.splitext(file.filename)[1]
        if not ext:
            ext = ".png"  # Default fallback
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(images_dir, filename)

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Return relative path for frontend to use
        # Assuming static mount is at /uploads
        relative_path = f"/uploads/images/{filename}"

        return {
            "success": True,
            "filename": filename,
            "file_path": relative_path,  # Frontend expects file_path
            "path": relative_path,
            "url": relative_path  # For compatibility
        }

    except Exception as e:
        print(f"Image upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_image(payload: dict = Body(...)):
    """
    Analyze an uploaded image and persist the result as image memory.
    Body: { image_path: str, prompt?: str }
    """
    try:
        image_path = payload.get("image_path")
        prompt = payload.get("prompt")
        if not image_path:
            raise HTTPException(
                status_code=400,
                detail="image_path is required"
            )

        tool = VisionTool()
        result = tool.analyze_image(image_path=image_path, prompt=prompt)

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "analysis failed")
            )

        # Build memory content and tag
        description = result.get("description", "").strip()
        face_info = result.get("face_info", "").strip()
        full_content = (f"{face_info}\n{description}").strip()

        # extract filename for tag suffix
        filename = os.path.basename(image_path) if image_path else "unknown"
        tag = f"image:{filename}"

        # Persist memory (with image_path)
        mem_id = None
        try:
            mm = MemoryManager()
            mem_id = mm.remember(full_content, tag=tag, image_path=image_path)
        except Exception as e:
            print(f"Persist image memory failed: {e}")

        return {
            "success": True,
            "data": {
                "description": description,
                "face_info": face_info,
                "face_details": result.get("face_details", []),
                "model": result.get("model", "unknown"),
                "memory_id": mem_id,
                "tag": tag
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Image analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
