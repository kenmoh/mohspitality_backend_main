from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import Item, Order, OrderItem, User
from app.schemas.order_schema import OrderCreate
from app.schemas.user_schema import OrderStatusEnum, UserType


async def create_order(order_data: OrderCreate, db: AsyncSession):
    """
    Create a new order with multiple items.
    """
    # Verify the outlet exists
    # This would be implemented based on your authentication/authorization system

    # Collect all item IDs to fetch in a single query
    item_ids = [item.item_id for item in order_data.items]

    # Fetch all items at once
    query = select(Item).where(Item.id.in_(item_ids))
    result = await db.execute(query)
    items = {item.id: item for item in result.scalars().all()}

    # Verify all requested items exist
    missing_items = set(item_ids) - set(items.keys())
    if missing_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Items with IDs {missing_items} not found",
        )

    # Create the order
    new_order = Order(
        outlet_id=order_data.outlet_id,
        company_id=order_data.company_id,
        guest_id=order_data.guest_id,
        status=OrderStatusEnum.NEW,
        total=Decimal(0),
        room_or_table_number=order_data.room_or_table_number,
    )

    # Add order items and calculate total
    total = Decimal(0)
    for item_data in order_data.items:
        item = items[item_data.item_id]

        # Create the order item
        order_item = OrderItem(
            item_id=item.id,
            quantity=item_data.quantity,
            price=item.price,
        )

        # Add to total
        item_total = item.price * Decimal(item_data.quantity)
        total += item_total

        # Add to order
        new_order.order_items.append(order_item)

    # Set the calculated total
    new_order.total = total

    # Save to database
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    return new_order


async def get_company_orders(
    current_user: User,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
):
    """
    Retrieve a list of orders with pagination, including their items.
    """
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    query = (
        select(Order)
        .where(Order.company_id == company_id)
        .options(selectinload(Order.order_items).selectinload(OrderItem.item))
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    orders = result.scalars().all()

    return orders


async def get_order_with_items(order_id: int, db: AsyncSession):
    """
    Retrieve an order by ID, including all order items and their associated items.
    """
    # Use selectinload to efficiently load the related order_items and items in a single query
    query = (
        select(Order)
        .options(selectinload(Order.order_items).selectinload(OrderItem.item))
        .where(Order.id == order_id)
    )

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    return order
