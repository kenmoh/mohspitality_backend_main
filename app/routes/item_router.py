from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.services import item_service
from app.schemas.item_schema import (
    CreateItemReturnSchema,
    CreateItemSchema,
    ItemStockReturnSchema,
    ItemStockSchema,
)

router = APIRouter(prefix="/api/items", tags=["Items"])


@router.post("/create-items", status_code=status.HTTP_201_CREATED)
async def create_item(
    data: CreateItemSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateItemSchema:
    try:
        return await item_service.create_item(
            data=data, current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{company_id}/get-items", status_code=status.HTTP_200_OK)
async def get_items(
    company_id: str,
    limit: int | None = None,
    skip: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CreateItemReturnSchema]:
    try:
        return await item_service.get_all_items(
            company_id=company_id,
            limit=limit,
            skip=skip,
            current_user=current_user,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{item_id}/item-details", status_code=status.HTTP_200_OK)
async def item_details(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateItemReturnSchema:
    try:
        return await item_service.get_item_by_id(
            item_id=item_id, current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{item_id}/get-items", status_code=status.HTTP_204_NO_CONTENT)
async def get_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await item_service.delete_item_by_id(
            item_id=item_id, current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{item_id}/stocks", status_code=status.HTTP_201_CREATED)
async def add_new_stock(
    item_id: int,
    stock: ItemStockSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemStockReturnSchema:
    try:
        return await item_service.add_new_stock(
            item_id=item_id, stock=stock, current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{stock_id}/update-stock", status_code=status.HTTP_202_ACCEPTED)
async def update_stock(
    stock_id: int,
    stock: ItemStockSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemStockReturnSchema:
    try:
        return await item_service.update_stock(
            stock_id=stock_id, stock=stock, current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
