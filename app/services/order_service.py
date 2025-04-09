from decimal import Decimal
import json
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from app.models.models import Item, Order, OrderItem, OrderSplit, User, UserProfile
from app.schemas.order_schema import (
    BillSplit,
    BillSplitResponse,
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusEnum,
    OrderSummaryResponse,
    UpdateOrderStatus,
)
from app.schemas.user_schema import UserType
from app.config.config import redis_client, settings
from app.services.profile_service import check_permission
from app.utils.utils import check_current_user_id, get_order_payment_link


async def create_order(order_data: OrderCreate, db: AsyncSession, current_user: User):
    """
    Create a new order with multiple items.
    """
    query = (
        select(User).options(joinedload(User.user_profile)).where(
            User.id == current_user.id)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    try:
        # Extract item IDs from request
        item_ids = [item.item_id for item in order_data.items]

        # Fetch items from database
        result = await db.execute(select(Item).where(Item.id.in_(item_ids)))
        items_dict = {item.id: item for item in result.scalars()}

        if not items_dict:
            raise HTTPException(
                status_code=400, detail="No valid items found.")

        # Validate item stock & calculate total price
        total_amount = Decimal(0)
        order_items = []
        item_details = []

        for item_data in order_data.items:
            item = items_dict.get(item_data.item_id)
            if not item:
                raise HTTPException(
                    status_code=400, detail=f"Item ID {item_data.item_id} not found."
                )

            if item.quantity < item_data.quantity:
                raise HTTPException(
                    status_code=400, detail=f"Insufficient stock for item {item.name}."
                )

            # Reduce stock
            item.quantity -= item_data.quantity

            order_item = OrderItem(
                item_id=item.id,
                quantity=item_data.quantity,
                price=item.price
            )

            order_items.append(order_item)

            # Store item details for response
            item_details.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "quantity": item_data.quantity,
                    "price": item.price,
                }
            )

            total_amount += item.price * item_data.quantity

        # Create order
        new_order = Order(
            guest_id=current_user.id,
            outlet_id=1,
            room_or_table_number=order_data.room_or_table_number,
            company_id=order_data.company_id,
            guest_name_or_email=user.user_profile.full_name
            if user.user_profile is not None
            else current_user.email,
            total_amount=total_amount,
            status=OrderStatusEnum.NEW,
            order_items=order_items,
        )

        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)

        # Generate order payment link
        payment_link = await get_order_payment_link(
            db=db,
            company_id=new_order.company_id,
            current_user=current_user,
            _id=new_order.id,
            amount=new_order.total_amount,
        )

        # # Update order with payment link
        new_order.payment_url = payment_link
        await db.commit()
        await db.refresh(new_order)

        # Build the order items response with names
        order_items_response = [
            OrderItemResponse(
                item_id=order_item.item_id,
                name=items_dict[order_item.item_id].name,
                quantity=order_item.quantity,
                price=order_item.price,
            )
            for order_item in new_order.order_items
        ]

        # Build the complete response
        response = OrderResponse(
            id=new_order.id,
            guest_id=new_order.guest_id,
            room_or_table_number=new_order.room_or_table_number,
            total_amount=new_order.total_amount,
            status=new_order.status,
            payment_url=new_order.payment_url,
            created_at=new_order.created_at,
            order_items=order_items_response,
        )

        company_orders_cache_key = f"orders:company:{new_order.company_id}"
        guest_orders_cache_key = f"orders:guest:{current_user.id}"
        redis_client.delete(company_orders_cache_key)
        redis_client.delete(guest_orders_cache_key)

        return response

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Order creation failed: {str(e)}")


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

    #check_permission(user=current_user, required_permission="update_orders")
    user_id = check_current_user_id(current_user=current_user)
    # Fetch the order to update
    query = select(Order).options(
            selectinload(Order.order_items)
            .joinedload(OrderItem.item)
        ).where(Order.id == order_id)
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
    new_total = Decimal("0.00")
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
    company_orders_cache_key = f"orders:company:{user_id}"
    redis_client.delete(company_orders_cache_key)

    order_cache_key = f"orders:guest:{user_id}"
    redis_client.delete(order_cache_key)

    #return {"order": order, "new_order_items": added_order_items}
    #return order
    
    # Construct the response with item names
    order_items_response = [
        OrderItemResponse(
            item_id=order_item.item_id,
            quantity=order_item.quantity,
            price=order_item.price,
            name=order_item.item.name  # Include the item name
        )
        for order_item in order.order_items
    ]
    
    order_response = OrderResponse(
        id=order.id,
        guest_id=order.guest_id,
        status=order.status,
        total_amount=order.total_amount,
        room_or_table_number=order.room_or_table_number,
        payment_url=order.payment_url or "",
        notes=order.notes,
        order_items=order_items_response
    )
    
    return order_response



async def get_order_summary(
    order_id: UUID, db: AsyncSession, current_user: User
) -> OrderSummaryResponse:
    """
    Retrieve an order summary that groups order items with the same item id.
    For each unique item, the summary includes the total quantity, individual price, and line total.
    Also returns the overall total amount for the order.


    """
    query = (
        select(Order)
        .options(selectinload(Order.order_items).selectinload(OrderItem.item))
        .where(Order.id == order_id)
        .where(Order.guest_id == current_user.id)
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
                "total": Decimal("0.00"),
            }
        summary[item.id]["quantity"] += order_item.quantity
        total = order_item.price * order_item.quantity
        summary[item.id]["total"] += total
        overall_total += total

    order_items_summary = {
        "order_id": order_id,
        "items": list(summary.values()),
        "total_amount": overall_total,
    }
    return OrderSummaryResponse(**order_items_summary)


async def split_bill(
    order_id: UUID, splits: list[BillSplit], db: AsyncSession, current_user: User
) -> BillSplitResponse:
    """
    Retrieve the order total, calculate splits, and create OrderSplit records.
    Each split can be defined by a fixed amount ("amount") or a percent ("percent").
    Returns the split allocation for each part and any remainder.
    """
    # Query the order's total amount
    query = (
        select(Order)
        .where(Order.id == order_id)
        .where(Order.guest_id == current_user.id)
    )
    result = await db.execute(query)
    
    order = result.scalar_one_or_none()
      
    total_amount = order.total_amount
    company_id = order.company_id

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
            part = split.value
        elif split.split_type == "percent":
            part = (total_amount * split.amount) / Decimal("100")
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid split type: {split.split_type}"
            )

        allocated += part
        # Create OrderSplit instance using the updated model
        order_split = OrderSplit(
            order_id=order_id,
            label=split.label,
            split_type=split.split_type,
            value=split.value,
            allocated_amount=part,
        )
        # Generate payment link for this split
        payment_url = await get_order_payment_link(
            db=db,
            company_id=company_id,
            current_user=current_user,
            _id=company_id,
            amount=part,
        )
        order_split.payment_url = payment_url
        order_split_instances.append(order_split)
        split_details.append(
            {
                "label": split.label,
                "split_type": split.split_type,
                "requested_value": str(split.value),
                "allocated": part,
                "payment_url": payment_url,
            }
        )

    remainder = total_amount - allocated

    # Check that the splits total equal to the order total.
    if remainder != Decimal("0.00"):
        raise HTTPException(
            status_code=400,
            detail=f"Sum of splits ({allocated}) does not equal order total ({total_amount}). Remainder: {remainder}",
        )

    # Persist the splits in the database
    for instance in order_split_instances:
        db.add(instance)
    await db.commit()

    return BillSplitResponse(
        order_id=order_id,
        total_amount=total_amount,
        splits=split_details,
        remainder=remainder,
    )


async def get_user_or_company_orders(current_user: User, db: AsyncSession):
    user_id = check_current_user_id(current_user)

    company_orders_cache_key = f"orders:company:{user_id}"
    guest_orders_cache_key = f"orders:guest:{user_id}"

    cached_orders = []

    if current_user.user_type == UserType.GUEST:
        cached_orders = redis_client.get(guest_orders_cache_key)
    else:
        cached_orders = redis_client.get(company_orders_cache_key)

    if cached_orders:
        json.loads(cached_orders)

    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.order_items)
            .joinedload(OrderItem.item)
        )
        .where(or_(Order.company_id == user_id, Order.guest_id == current_user.id))
    )

    orders = result.unique().scalars().all()

    order_responses = []
    for order in orders:
        order_items_response = [
            OrderItemResponse(
                item_id=order_item.item_id,
                quantity=order_item.quantity,
                price=order_item.price,
                name=order_item.item.name
            )
            for order_item in order.order_items
        ]

        order_response = OrderResponse(
            id=order.id,
            guest_id=order.guest_id,
            status=order.status,
            total_amount=order.total_amount,
            room_or_table_number=order.room_or_table_number,
            payment_url=order.payment_url or "",  # Handle None values
            notes=order.notes,
            order_items=order_items_response
        )
        order_responses.append(order_response)

        # Cache the results
        cache_data = json.dumps([order.model_dump()
                                for order in order_responses], default=str)
        if current_user.user_type == UserType.GUEST:
            redis_client.set(guest_orders_cache_key,
                             cache_data, ex=settings.REDIS_EX)
        else:
            redis_client.set(company_orders_cache_key,
                             cache_data, ex=settings.REDIS_EX)

    return order_responses


async def update_order_status(
    order_id: UUID, db: AsyncSession, current_user: User, status_data: UpdateOrderStatus
):
    check_permission(user=current_user, required_permission="update_orders")

    user_id = check_current_user_id(current_user)
    stmt = select(Order).where(Order.id == order_id,
                               Order.company_id == user_id)

    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    order.status = status_data.status

    await db.commit()
    await db.refresh(order)

    company_order_cache_key = f"orders:company:{user_id}"
    guest_order_cache_key = f"orders:guest:{user_id}"
    redis_client.delete(company_order_cache_key)
    redis_client.delete(guest_order_cache_key)

    return order


# d68bbf86-0ad8-11f0-9558-75b24b59bc1c
