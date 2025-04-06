from uuid import UUID
from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.reservation_schema import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)
from app.services import reservation_service


router = APIRouter(prefix="/reservations", tags=["Restaurant Reservations"])


@router.get("", status_code=status.HTTP_200_OK)
async def get_reservations(
    limit: int = None,
    skip: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationResponse]:
    try:
        return await reservation_service.get_user_reservations(
            limit=limit, skip=skip, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_reservation(
    data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationResponse]:
    try:
        return await reservation_service.create_reservation(
            reservation_data=data, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{reservation_id}/update", status_code=status.HTTP_202_ACCEPTED)
async def update_reservation(
    reservation_id: UUID,
    data: ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationResponse]:
    try:
        return await reservation_service.update_reservation(
            reservation_id=reservation_id,
            reservation_data=data,
            db=db,
            current_user=current_user,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{reservation_id}", status_code=status.HTTP_200_OK)
async def reservation_details(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReservationResponse]:
    try:
        return await reservation_service.reservation_details(
            reservation_id=reservation_id, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
