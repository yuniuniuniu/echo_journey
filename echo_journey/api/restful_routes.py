import json

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()

@router.post("/diagnoses")
async def upload_image(file: UploadFile = File(...)):
    pass
