from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.order_schema import BillSplit, OrderCreate, OrderResponse
from app.services import order_service


router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("/order-details", status_code=status.HTTP_200_OK)
async def order_details(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Retrieve an order with its items.
    """
    try:
        return await order_service.get_order_with_items(
            order_id=order_id, db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/company-orders", status_code=status.HTTP_200_OK)
async def get_all_company_orders(
    skip: int | None = None,
    limit: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Retrieve a list of orders with pagination, including their items.

    Args:
        skip (int | None, optional): Number of records to skip. Defaults to None.
        limit (int | None, optional): Number of records to return. Defaults to None.
        current_user (User, optional): Current user. Defaults to Depends(get_current_user).
        db (AsyncSession, optional): Database session. Defaults to Depends(get_db).

        Returns:
            list[OrderResponse]: A list of orders.
    """
    try:
        return await order_service.get_company_orders(
            current_user=current_user, db=db, skip=skip, limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update-order", status_code=status.HTTP_202_ACCEPTED)
async def update_order(
    order_id: UUID,
    order_data: OrderCreate,
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
            current_user=current_user, db=db, order_data=order_data, order_id=order_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/order-summary", status_code=status.HTTP_200_OK)
async def order_summary(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
