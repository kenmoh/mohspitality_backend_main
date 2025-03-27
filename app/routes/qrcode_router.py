import io
import os
from fastapi import APIRouter, Depends, HTTPException, status

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.room_schema import QRCodeCreate, QRCodeResponse
from app.services import qrcode_service


router = APIRouter(prefix="/api/qrcodes", tags=["QRCodes"])


@router.post("/generate-qrcodes", status_code=status.HTTP_201_CREATED)
async def generate_qrcode(
    qrcode_data: QRCodeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        zip_path = await qrcode_service.create_qrcode(
            current_user=current_user, db=db, qrcode_data=qrcode_data
        )
        with open(zip_path, "rb") as file:
            zip_content = io.BytesIO(file.read())
        os.remove(zip_path)

        headers = {
            "Content-Disposition": f"attachment; filename={zip_path}",
            "Content-Type": "application/zip",
        }
        return StreamingResponse(
            zip_content, headers=headers, media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/generate-qrcodes", status_code=status.HTTP_200_OK)
async def get_qrcodes(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[QRCodeResponse]:
    return await qrcode_service.get_qrcode(db=db, current_user=current_user)
