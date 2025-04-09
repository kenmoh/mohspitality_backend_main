from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.order_schema import (
    BillSplit,
    OrderCreate,
    OrderResponse,
    UpdateOrderStatus,
    OrderSummaryResponse
)
from app.services import order_service


router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Place a new order.

    Args:
        order_data (OrderCreate): Order data to be created.
        current_user (User, optional): Current user. Defaults to Depends(get_current_user).
        db (AsyncSession, optional): Database session. Defaults to Depends(get_db).

    Returns:
        OrderResponse: The created order.
    """
    try:
        return await order_service.create_order(
            current_user=current_user, db=db, order_data=order_data
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update-order", status_code=status.HTTP_202_ACCEPTED)
async def update_order(
    order_id: UUID,
    new_items: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update an order with new item(s).

    Args:
        order_id (UUID): Order ID.
        order_data (OrderCreate): Order data to be created.
        current_user (User, optional): Current user. Defaults to Depends(get_current_user).
        db (AsyncSession, optional): Database session. Defaults to Depends(get_db).

    Returns:
        OrderResponse: The created order.
    """
    try:
        return await order_service.update_order(
            current_user=current_user, db=db, new_items=new_items, order_id=order_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update-order-status", status_code=status.HTTP_202_ACCEPTED)
async def update_order_status(
    order_id: UUID,
    status_data: UpdateOrderStatus,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpdateOrderStatus:
    """Update an order with new item(s).

    - Args:
        - order_id.
        - order_data
        - Current user.
        - Database session.

    - Returns:
        - The updated order status.
    """
    try:
        return await order_service.update_order_status(
            current_user=current_user, db=db, status_data=status_data, order_id=order_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/order-summary", status_code=status.HTTP_200_OK)
async def order_summary(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderSummaryResponse:
    """Retrieve an order summary.
    Args:

        order_id (UUID): Order ID.
        current_user (User, optional): Current user. Defaults to Depends(get_current_user).
        db (AsyncSession, optional): Database session. Defaults to Depends(get_db).

        Returns:
            OrderResponse: The order summary.
    """
    try:
        return await order_service.get_order_summary(
            current_user=current_user, db=db, order_id=order_id
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/split-bill", status_code=status.HTTP_201_CREATED)
async def split_bill(
    order_id: UUID,
    splits: list[BillSplit],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Split a bill.
    Args:
        order_id (UUID): Order ID.
        current_user (User, optional): Current user. Defaults to Depends(get_current_user).
        db (AsyncSession, optional): Database session. Defaults to Depends(get_db).

    Returns:
        OrderResponse: split order.
    """
    try:
        return await order_service.split_bill(
            current_user=current_user, db=db, order_id=order_id, splits=splits
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/user-orders", status_code=status.HTTP_200_OK)
async def user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Retrieve user/company orders.
    Args:
        Current user.
       Database session.
    Returns:
        The current guest or company orders.
    """
    try:
        return await order_service.get_user_or_company_orders(
            current_user=current_user, db=db
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
