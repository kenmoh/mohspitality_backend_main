from uuid import UUID
import json
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Item, ItemStock, User
from app.schemas.item_schema import (
    CreateItemReturnSchema,
    CreateItemSchema,
    ItemStockSchema,
    ItemStockReturnSchema,
)
from app.schemas.user_schema import UserType
from app.services.profile_service import check_permission
from app.config.config import redis_client, settings
from app.utils.utils import get_company_id


async def create_item(
    data: CreateItemSchema, db: AsyncSession, current_user: User
) -> CreateItemReturnSchema:
    """
    Create a new item in the database.
    """
    check_permission(user=current_user, required_permission="create_items")

    cache_key = f"items:{company_id}"

    company_id = get_company_id(current_user)
    try:
        new_item = Item(
            name=data.name,
            description=data.description,
            unit=data.unit,
            reorder_point=data.reorder_point,
            price=data.price,
            image_url=data.image_url,
            category=data.category,
            company_id=company_id,
        )

        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        redis_client.delete(cache_key)

        return new_item
    except Exception as e:
        await db.rollback()
        raise Exception(str(e))


async def get_item_by_id(
    db: AsyncSession, item_id: int, current_user: User
) -> CreateItemReturnSchema:
    """
    Retrieve an item by its ID.
    """
    company_id = get_company_id(current_user)
    result = await db.execute(
        select(Item)
        .options(joinedload(Item.stocks))
        .where(Item.id == item_id, Item.company_id == company_id)
    )

    return result.scalars().first()


async def update_item_item_by_id(
    db: AsyncSession, item_id: int, item_data: CreateItemSchema, current_user: User
) -> CreateItemSchema:
    await check_permission(user=current_user, required_permission="update_items")
    company_id = get_company_id(current_user)
    """
    Update an existing item.
    """
    cache_key = f"items:{company_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    stmt = (
        update(Item)
        .where((Item.id == item_id) & Item.company_id == company_id)
        .values(**item_data.model_dump(exclude_unset=True))
        .execution_options(synchronize_session="fetch")
    )
    result = await db.execute(stmt)

    redis_client.set(cache_key, json.dumps(
        result, default=str), ex=settings.REDIS_EX)

    await db.commit()
    return await result.scalar_one_or_none()


async def get_all_items(
    db: AsyncSession,
    company_id: UUID,
    limit: int = 10,
    skip: int = 0,
) -> list[CreateItemReturnSchema]:
    """
    Retrieve all company items with pagination.
    """
    # company_id = current_user.id if current_user.user_type == UserType.COMPANY else current_user.company_id
    cache_key = f"items:{company_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    result = await db.execute(
        select(Item)
        .options(joinedload(Item.stocks))
        .where(Item.company_id == company_id)
        .offset(skip)
        .limit(limit)
    )
    items = result.unique().scalars().all()
    items_data = [
        CreateItemReturnSchema.model_validate(item).model_dump() for item in items
    ]

    redis_client.set(
        cache_key, json.dumps(items_data, default=str), ex=settings.REDIS_EX
    )
    return items_data


async def delete_item_by_id(db: AsyncSession, item_id: int, current_user: User) -> None:
    """
    Delete an item by its ID.
    """
    await check_permission(user=current_user, required_permission="delete_items")
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    stmt = delete(Item).where(Item.id == item_id &
                              Item.company_id == company_id)
    await db.execute(stmt)
    await db.commit()
    return None


async def add_new_stock(
    item_id: int, current_user: User, db: AsyncSession, stock: ItemStockSchema
) -> ItemStockReturnSchema:
    check_permission(user=current_user, required_permission="create_stocks")

    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.company_id == company_id)
    )

    item = result.scalar_one_or_none()

    if not item:
        raise Exception(f"Item with ID {item_id} not found")

    try:
        new_stock = ItemStock(
            item_id=item_id,
            company_id=company_id,
            quantity=stock.quantity,
            notes=stock.notes,
        )

        db.add(new_stock)
        await db.flush()

        item.quantity += new_stock.quantity
        await db.commit()
        await db.refresh(new_stock)

        return new_stock
    except Exception as e:
        await db.rollback()
        raise Exception(str(e))


async def update_stock(
    stock_id: int, current_user: User, db: AsyncSession, stock: ItemStockSchema
) -> ItemStockReturnSchema:
    """
    Update an existing stock entry and reflect changes in the item's quantity.
    """
    check_permission(user=current_user, required_permission="update_stocks")

    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )

    # Find the stock entry
    result = await db.execute(
        select(ItemStock).where(
            ItemStock.id == stock_id, ItemStock.company_id == company_id
        )
    )
    existing_stock = result.scalar_one_or_none()

    if not existing_stock:
        raise Exception(f"Stock with ID {stock_id} not found")

    # Get the associated item
    item_result = await db.execute(
        select(Item).where(
            Item.id == existing_stock.item_id, Item.company_id == company_id
        )
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise Exception(
            f"Associated item with ID {existing_stock.item_id} not found")

    try:
        # Remove existing stock quantity from item quantity
        item.quantity -= existing_stock.quantity

        # Update the stock entry
        existing_stock.quantity = stock.quantity
        existing_stock.notes = stock.notes

        await db.flush()

        # Update the item's total quantity
        item.quantity += existing_stock.quantity

        await db.commit()
        await db.refresh(existing_stock)

        return existing_stock
    except Exception as e:
        await db.rollback()
        raise Exception(str(e))
