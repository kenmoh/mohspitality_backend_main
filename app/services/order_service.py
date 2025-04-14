from decimal import Decimal
import json
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from app.models.models import Item, Order, OrderItem, User, UserProfile
from app.schemas.order_schema import (
    OrderSplitRequest,
    BillSplitResponse,
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatusEnum,
    OrderSummaryResponse,
    UpdateOrderStatus,
    PaymentStatus,
)
from app.schemas.user_schema import UserType
from app.config.config import redis_client, settings
from app.services.profile_service import check_permission
from app.utils.utils import get_company_id, get_order_payment_link
from app.services.notification_service import manager


async def create_order(order_data: OrderCreate, db: AsyncSession, current_user: User):
    """
    Create a new order with multiple items.
    """
    query = (
        select(User)
        .options(joinedload(User.user_profile))
        .where(User.id == current_user.id)
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
                item_id=item.id, quantity=item_data.quantity, price=item.price
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
            is_split=False,
            room_or_table_number=order_data.room_or_table_number,
            company_id=order_data.company_id,
            guest_name_or_email=user.user_profile.full_name
            if user.user_profile is not None
            else current_user.email,
            total_amount=total_amount,
            status=OrderStatusEnum.NEW,
            order_items=order_items,
            payment_type=PaymentStatus.PENDING,
            notes=order_data.notes if order_data.notes else None,
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

        # # Update order with payment link and original order ID
        new_order.payment_url = payment_link
        new_order.original_order_id = new_order.id

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
            original_order_id=new_order.original_order_id,
            created_at=new_order.created_at,
            order_items=order_items_response,
        )

        company_orders_cache_key = f"orders:company:{new_order.company_id}"
        guest_orders_cache_key = f"orders:guest:{current_user.id}"
        redis_client.delete(company_orders_cache_key)
        redis_client.delete(guest_orders_cache_key)

        # Notify company about the new order
        await manager.notify_new_order(company_id=response.company_id, room_or_table_number=response.room_or_table_number)

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

    # check_permission(user=current_user, required_permission="update_orders")
    user_id = get_company_id(current_user) if (
        current_user.user_type == UserType.COMPANY or current_user.user_type == UserType.STAFF) else current_user.id
    # Fetch the order to update
    query = (
        select(Order)
        .options(selectinload(Order.order_items).joinedload(OrderItem.item))
        .where(Order.id == order_id)
    )
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

    # return {"order": order, "new_order_items": added_order_items}
    # return order

    # Construct the response with item names
    order_items_response = [
        OrderItemResponse(
            item_id=order_item.item_id,
            quantity=order_item.quantity,
            price=order_item.price,
            name=order_item.item.name,  # Include the item name
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
        order_items=order_items_response,
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


async def split_order(
    order_id: UUID,
    split_request: OrderSplitRequest,
    current_user: User,
    db: AsyncSession,
):
    """
    Create a new order with multiple items from an existing order.
    By default, split orders are not sent to kitchen unless explicitly requested.
    """
    # Get the original order with locking to prevent concurrent modifications

    original_order = await db.execute(
        select(Order)
        .with_for_update()
        .options(selectinload(Order.order_items).joinedload(OrderItem.item))
        .where(Order.id == order_id)
        .where(Order.guest_id == current_user.id)
    )
    original_order = original_order.scalar_one_or_none()

    if not original_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check if order can be split (status should be NEW)
    # if original_order.status != OrderStatusEnum.NEW:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Only orders with status NEW can be split",
    #     )

    try:
        # Validate split items against original order
        total_amount = Decimal(0)
        new_order_items = []
        items_to_update = []

        # Create mapping of original order items for quick lookup
        original_items_map = {
            oi.item_id: oi for oi in original_order.order_items}

        for item_request in split_request.items:
            original_item = original_items_map.get(item_request.item_id)

            if not original_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item {item_request.item_id} not found in original order",
                )

            if item_request.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Quantity for item {item_request.item_id} must be positive",
                )

            if original_item.quantity < item_request.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough quantity for item {original_item.item.name} "
                    f"(requested {item_request.quantity}, available {original_item.quantity})",
                )

            # Calculate amount for this item
            item_amount = original_item.price * Decimal(item_request.quantity)
            total_amount += item_amount

            # Create new order item for split order
            new_order_item = OrderItem(
                item_id=original_item.item_id,
                quantity=item_request.quantity,
                price=original_item.price,
            )
            new_order_items.append(new_order_item)

            # Track items to update in original order
            items_to_update.append(
                {
                    "original_item": original_item,
                    "split_quantity": item_request.quantity,
                    "item_amount": item_amount,
                }
            )

        # Create the split order
        split_order = Order(
            guest_id=original_order.guest_id,
            outlet_id=original_order.outlet_id,
            company_id=original_order.company_id,
            guest_name_or_email=original_order.guest_name_or_email,
            total_amount=total_amount,
            room_or_table_number=original_order.room_or_table_number,
            payment_type=original_order.payment_type,
            order_items=new_order_items,
            original_order_id=original_order.id,
            is_split=True,
        )
        db.add(split_order)
        await db.flush()

        # Update original order items
        for item_data in items_to_update:
            original_item = item_data["original_item"]
            split_quantity = item_data["split_quantity"]

            # Reduce quantity in original order
            original_item.quantity -= split_quantity
            original_order.total_amount -= item_data["item_amount"]

            # Remove item if quantity reaches zero
            if original_item.quantity <= 0:
                await db.delete(original_item)

        # Generate payment link for the split order
        split_order_payment_link = await get_order_payment_link(
            db=db,
            company_id=split_order.company_id,
            current_user=current_user,
            _id=split_order.id,
            amount=split_order.total_amount,
        )
        original_order_payment_link = await get_order_payment_link(
            db=db,
            company_id=split_order.company_id,
            current_user=current_user,
            _id=split_order.id,
            amount=original_order.total_amount - (split_order.total_amount),
        )
        split_order.payment_url = split_order_payment_link
        original_order.payment_url = original_order_payment_link

        await db.commit()
        await db.refresh(split_order)

        # Build the order items response with names
        order_items_response = [
            OrderItemResponse(
                item_id=order_item.item_id,
                name=order_item.item.name,
                quantity=order_item.quantity,
                price=order_item.price,
            )
            for order_item in split_order.order_items
        ]

        # Build the complete response
        response = OrderResponse(
            id=split_order.id,
            guest_id=split_order.guest_id,
            room_or_table_number=split_order.room_or_table_number,
            total_amount=split_order.total_amount,
            status=split_order.status,
            payment_url=split_order.payment_url,
            original_order_id=split_order.original_order_id,
            created_at=split_order.created_at,
            order_items=order_items_response,
        )

        # Clear relevant caches
        company_orders_cache_key = f"orders:company:{split_order.company_id}"
        guest_orders_cache_key = f"orders:guest:{current_user.id}"
        redis_client.delete(company_orders_cache_key)
        redis_client.delete(guest_orders_cache_key)

        return response

    except HTTPException as http_ex:
        await db.rollback()
        raise http_ex
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Order splitting failed: {str(e)}")


async def get_split_orders(
    original_order_id: UUID, current_user: User, db: AsyncSession
) -> list[OrderResponse]:
    """
    Retrieve the original order and all orders that were split from it
    """
    # Get the original order with its items
    original_order = await db.execute(
        select(Order)
        .where(Order.id == original_order_id)
        .where(Order.guest_id == current_user.id)
        .options(selectinload(Order.order_items).joinedload(OrderItem.item))
    )
    original_order = original_order.scalar_one_or_none()

    if not original_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Original order not found"
        )

    # Get all split orders with their items
    split_orders_result = await db.execute(
        select(Order)
        .where(Order.original_order_id == original_order_id)
        .options(selectinload(Order.order_items).joinedload(OrderItem.item))
    )
    split_orders = split_orders_result.scalars().all()

    # Prepare response list
    response = []

    # Format split orders
    for order in split_orders:
        order_items_response = [
            OrderItemResponse(
                item_id=order_item.item_id,
                name=order_item.item.name,
                quantity=order_item.quantity,
                price=order_item.price,
            )
            for order_item in order.order_items
        ]

        response.append(
            OrderResponse(
                id=order.id,
                guest_id=order.guest_id,
                room_or_table_number=order.room_or_table_number,
                total_amount=order.total_amount,
                status=order.status.value
                if hasattr(order.status, "value")
                else order.status,
                payment_url=order.payment_url,
                original_order_id=order.original_order_id,
                order_items=order_items_response,
                is_split=order.is_split,
                notes=order.notes,
            )
        )

    return response


async def delete_split_order(
    split_order_id: UUID, current_user: User, db: AsyncSession
) -> None:
    """
    Delete a split order and return its items to the original order.
    Returns the updated original order.
    """

    try:
        # Get the split order with items and their original items
        split_order = await db.execute(
            select(Order)
            .where(Order.id == split_order_id)
            .where(Order.guest_id == current_user.id)
            .where(Order.is_split == True)
            .options(selectinload(Order.order_items).joinedload(OrderItem.item))
        )
        split_order = split_order.scalar_one_or_none()

        if not split_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Split order not found or not eligible for deletion",
            )

        if not split_order.original_order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This is not a split order",
            )

        # Get the original order with items
        original_order = await db.execute(
            select(Order)
            .where(Order.id == split_order.original_order_id)
            .options(selectinload(Order.order_items).joinedload(OrderItem.item))
            .with_for_update()  # Lock for update
        )
        original_order = original_order.scalar_one_or_none()

        # Process each item in the split order
        for split_item in split_order.order_items:
            # Find corresponding item in original order
            original_item = next(
                (
                    oi
                    for oi in original_order.order_items
                    if oi.item_id == split_item.item_id
                ),
                None,
            )

            if original_item:
                # Item exists in original order - just increase quantity
                original_item.quantity += split_item.quantity
            else:
                # Item doesn't exist in original order - add it back
                new_order_item = OrderItem(
                    item_id=split_item.item_id,
                    quantity=split_item.quantity,
                    price=split_item.price,
                )
                original_order.order_items.append(new_order_item)

            # Update the original order total
            original_order.total_amount += split_item.price * split_item.quantity

        # Update original order status if needed
        if not original_order.is_split:
            original_order.is_split = False

        # Generate new payment link for original order
        original_order.payment_url = await get_order_payment_link(
            db=db,
            company_id=original_order.company_id,
            current_user=current_user,
            _id=original_order.id,
            amount=original_order.total_amount,
        )

        # Delete the split order
        await db.delete(split_order)
        await db.commit()

        return None

    except HTTPException as http_ex:
        await db.rollback()
        raise http_ex
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete split order: {str(e)}",
        )


async def get_user_or_company_orders(current_user: User, db: AsyncSession):
    user_id = get_company_id(current_user) if (
        current_user.user_type == UserType.COMPANY or current_user.user_type == UserType.STAFF)else current_user.id

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
        .options(selectinload(Order.order_items).joinedload(OrderItem.item))
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
                name=order_item.item.name,
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
            order_items=order_items_response,
        )
        order_responses.append(order_response)

        # Cache the results
        cache_data = json.dumps(
            [order.model_dump() for order in order_responses], default=str
        )
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

    user_id = get_company_id(current_user)
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
