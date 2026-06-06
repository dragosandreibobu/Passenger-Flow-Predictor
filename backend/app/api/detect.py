from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from app.services.vision import process_image
from typing import Optional

router = APIRouter()

@router.post("/detect")
async def detect_people(
    file: UploadFile = File(...),
    camera_id: Optional[str] = Form("cam_checkin_01")
):
    result = await process_image(file, camera_id)
    return JSONResponse(content=result)
