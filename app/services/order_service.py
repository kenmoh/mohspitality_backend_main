import asyncio
from decimal import Decimal
import json
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.models import Item, Order, OrderItem, OrderSplit, User
from app.schemas.order_schema import BillSplit, OrderCreate, OrderResponse, OrderStatusEnum
from app.schemas.user_schema import UserType
from app.config.config import redis_client, settings
from app.utils.utils import get_order_payment_link


"""

 async def create_parent(db: AsyncSession) -> Parent:
            parent = Parent()
            db.add(parent)
            await db.commit()

            result = await db.execute(
                select(Parent)
                .options(joinedload(Parent.children))
                .where(Parent.id == parent.id)
            )
            parent = result.scalars().unique().one()

            print(parent.children_count)  # works properly now
"""


# async def create_order(order_data: OrderCreate, db: AsyncSession, current_user: User):
#     """
#     Create a new order with multiple items.
#     """
#     # Verify the outlet exists

#     # Collect all item IDs to fetch in a single query
#     item_ids = [item.item_id for item in order_data.items]

#     # Fetch all items at once
#     items = await db.execute(
#         select(Item).where(Item.id.in_(item_ids)).execution_options(populate_existing=True)
#     )
#     #query = select(Item).where(Item.id.in_(item_ids))
#     #result = await db.execute(query)
#     items = {item.id: item for item in items.scalars().all()}

#     print(items, '==================-========-=========================')


#     # Verify all requested items exist
#     missing_items = set(item_ids) - set(items.keys())
#     if missing_items:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Items with IDs {missing_items} not found",
#         )

#     try:
#         # Create the order
#         new_order = Order(
#             outlet_id=order_data.outlet_id,
#             company_id=order_data.company_id,
#             guest_name_or_email=current_user.user_profile.full_name if current_user.user_profile.full_name else current_user.email,
#             guest_id=current_user.id,
#             status=OrderStatusEnum.NEW,
#             total_amount=Decimal('0.00'),
#             room_or_table_number=order_data.room_or_table_number,
#             order_items=[],
#         )


#         # Add order items and calculate total
#         total_amount = Decimal('0.00')

#         for item_data in order_data.items:
#             item = items[item_data.item_id]

#             # Create the order item
#             order_item = OrderItem(
#                 item_id=item.id,
#                 quantity=item_data.quantity,
#                 price=item.price,
#             )

#             # Add to total
#             item_total = item.price * Decimal(item_data.quantity)
#             total_amount += item_total

#             # Add to order
#             new_order.order_items.append(order_item)

#         # Set the calculated total
#         new_order.total_amount = total_amount

#         # Save to database
#         db.add(new_order)
#         await db.commit()
#         await db.refresh(new_order)

#         company_orders_cache_key = f"orders:company:{new_order.company_id}"
#         redis_client.delete(company_orders_cache_key)

#         return new_order
#     except Exception as e:
#         await db.rollback()
#         raise Exception(str(e))

async def create_order(order_data: OrderCreate, db: AsyncSession, current_user: User):
    """
    Create a new order with multiple items.
    """

    # Load all items in one query (awaited)
    item_ids = [item.item_id for item in order_data.items]
    items = await db.execute(
        select(Item).where(Item.id.in_(item_ids)
                           ).execution_options(populate_existing=True)
    )
    items = {item.id: item for item in items.scalars().all()}

    # Verify all items exist
    if missing_items := set(item_ids) - set(items.keys()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Items with IDs {missing_items} not found",
        )

    try:
        # Build order with proper relationship loading
        new_order = Order(
            outlet_id=order_data.outlet_id,
            company_id=order_data.company_id,
            guest_name_or_email=current_user.user_profile.full_name if current_user.user_profile else current_user.email,
            guest_id=current_user.id,
            status=OrderStatusEnum.NEW,
            total_amount=Decimal('0.00'),
            room_or_table_number=order_data.room_or_table_number,
            splits=[],
            order_items=[],
        )

        # Add items with explicit relationship handling
        total_amount = Decimal('0.00')
        for item_data in order_data.items:
            item = items[item_data.item_id]
            new_order.order_items.append(OrderItem(
                item_id=item.id,
                quantity=item_data.quantity,
                price=item.price,
            ))
            total_amount += item.price * Decimal(str(item_data.quantity))

        new_order.total_amount = 4500
        new_order.payment_link = await get_order_payment_link(order=new_order, db=db, current_user=current_user)

        # Save with explicit flush/commit (awaited)
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        # Sync Redis operation (no await!)
        redis_client.delete(f"orders:company:{new_order.company_id}")

        return new_order

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order creation failed: {str(e)}"
        )


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
    cache_key = f"orders:company:{company_id}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    query = (
        select(Order)
        .where(Order.company_id == company_id)
        .options(selectinload(Order.order_items).selectinload(OrderItem.item))
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    orders = result.scalars().all()

    await redis_client.set(cache_key, json.dumps(orders), ex=settings.REDIS_EX)

    return orders


async def get_order_with_items(order_id: UUID, db: AsyncSession):
    """
    Retrieve an order by ID, including all order items and their associated items.
    """
    # Use selectinload to efficiently load the related order_items and items in a single query
    cache_key = f"order:{order_id}"
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

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
    await redis_client.set(cache_key, json.dumps(order), ex=settings.REDIS_EX)
    return order


async def update_order(
    order_id: UUID,
    new_items: OrderCreate,
    db: AsyncSession,
    current_user: User,
) -> OrderResponse:
    """
    Append new order items to an existing order without merging with existing items.
    This allows the guest to add the same order item again as a separate record.
    Recalculate the total and invalidate the related caches.
    Returns a dict containing the updated order and the newly added order items.
    """
    # Fetch the order to update
    query = select(Order).where(Order.id == order_id)
    result = await db.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    # Collect IDs for new items and query the Item objects
    new_item_ids = [item.item_id for item in new_items.items]
    query_items = select(Item).where(Item.id.in_(new_item_ids))
    result_items = await db.execute(query_items)
    items = {item.id: item for item in result_items.scalars().all()}

    # Check for missing items
    missing_items = set(new_item_ids) - set(items.keys())
    if missing_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Items with IDs {missing_items} not found",
        )

    # Process each new item: create order items and update total
    new_total = Decimal('0.00')
    added_order_items = []
    for item_data in new_items.items:
        item = items[item_data.item_id]
        order_item = OrderItem(
            item_id=item.id,
            quantity=item_data.quantity,
            price=item.price,
        )
        # Calculate the total for this item and add to overall new total
        item_total = item.price * Decimal(item_data.quantity)
        new_total += item_total

        # Always append the new order item, even if it's a duplicate of an existing one
        order.order_items.append(order_item)
        added_order_items.append(order_item)

    # Update order total amount
    order.total_amount += new_total

    # Save updates to database
    await db.commit()
    await db.refresh(order)

    # Invalidate caches (both company orders and individual order cache)
    company_orders_cache_key = f"orders:company:{order.company_id}"
    await redis_client.delete(company_orders_cache_key)

    order_cache_key = f"order:{order_id}"
    await redis_client.delete(order_cache_key)

    return {"order": order, "new_order_items": added_order_items}


async def get_order_summary(order_id: UUID, db: AsyncSession, current_user: User) -> dict:
    """
    Retrieve an order summary that groups order items with the same item id.
    For each unique item, the summary includes the total quantity, individual price, and line total.
    Also returns the overall total amount for the order.
    """
    query = (
        select(Order)
        .options(selectinload(Order.order_items).selectinload(OrderItem.item))
        .where(Order.id == order_id).where(Order.guest_id == current_user.id)
    )
    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID {order_id} not found",
        )

    summary = {}
    overall_total = Decimal("0.00")

    for order_item in order.order_items:
        item = order_item.item  # Retrieve the associated Item via relationship
        # Group by item ID
        if item.id not in summary:
            summary[item.id] = {
                "item_id": item.id,
                "name": item.name,
                "quantity": 0,
                "price": order_item.price,
                "total": Decimal("0.00")
            }
        summary[item.id]["quantity"] += order_item.quantity
        total = order_item.price * order_item.quantity
        summary[item.id]["total"] += total
        overall_total += total

    return {"order_id": order_id, "items": list(summary.values()), "total_amount": overall_total}


async def split_bill(order_id: UUID, splits: list[BillSplit], db: AsyncSession, current_user: User) -> dict:
    """
    Retrieve the order total, calculate splits, and create OrderSplit records.
    Each split can be defined by a fixed amount ("amount") or a percent ("percent").
    Returns the split allocation for each part and any remainder.
    """
    # Query the order's total amount
    query = select(Order.total_amount).where(
        Order.id == order_id).where(Order.guest_id == current_user.id)
    result = await db.execute(query)
    total_amount = result.scalar_one_or_none()

    if total_amount is None:
        raise HTTPException(
            status_code=404,
            detail=f"Order with ID {order_id} not found",
        )

    allocated = Decimal("0.00")
    split_details = []
    order_split_instances = []

    for split in splits:
        if split.split_type == "amount":
            part = split.amount
        elif split.split_type == "percent":
            part = (total_amount * split.amount) / Decimal("100")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid split type: {split.split_type}"
            )

        allocated += part
        # Create OrderSplit instance using the updated model
        order_split = OrderSplit(
            order_id=order_id,
            label=split.label,
            split_type=split.split_type,
            value=split.value,
            allocated_amount=part
        )
        order_split_instances.append(order_split)
        split_details.append({
            "label": split.label,
            "split_type": split.split_type,
            "requested_value": str(split.value),
            "allocated": str(part),
        })

    remainder = total_amount - allocated

    # Check that the splits total equal to the order total.
    # For example:
    if remainder != Decimal("0.00"):
        raise HTTPException(
            status_code=400,
            detail=f"Sum of splits ({allocated}) does not equal order total ({total_amount}). Remainder: {remainder}"
        )

    # Persist the splits in the database
    for instance in order_split_instances:
        db.add(instance)
    await db.commit()
    await db.refresh(instance)

    return {
        "order_id": str(order_id),
        "total_amount": str(total_amount),
        "splits": split_details,
        "remainder": str(remainder)
    }
