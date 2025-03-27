from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.order_schema import OrderResponse
from app.services import order_service


router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/company-orders", status_code=status.HTTP_200_OK)
async def get_all_company_orders(
    skip: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    try:
        return await order_service.get_company_orders(
            current_user=current_user, db=db, skip=skip, limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
