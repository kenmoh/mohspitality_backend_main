import json
from operator import or_
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, RestaurantReservation
from app.schemas.reservation_schema import ReservationCreate, ReservationResponse
from app.schemas.user_schema import UserType
from app.utils.utils import get_order_payment_link
from app.config.config import settings, redis_client


async def create_reservations(
    company_id: UUID, data: ReservationCreate, current_user: User, db: AsyncSession
) -> ReservationResponse:
    # await check_permission(user=current_user, required_permission='create_rate')

    try:
        # Create a new reservation
        new_reservation = RestaurantReservation(
            guest_id=current_user.id,
            company_id=company_id,
            guest_name=data.name,
            date=data.date,
            time=data.time,
            notes=data.notes,
            deposit_amount=data.deposit_amount,
            adult=data.adult,
            children=data.children,
        )

        db.add(new_reservation)
        await db.flush(new_reservation)

        if new_reservation.deposit_amount > 0:
            new_reservation.payment_link = await get_order_payment_link(
                db=db,
                current_user=current_user,
                amount=new_reservation.deposit_amount,
                _id=new_reservation.id,
                company_id=new_reservation.company_id,
            )

        await db.commit()
        await db.refresh(new_reservation)

        return new_reservation
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def get_user_reservations(
    db: AsyncSession,
    current_user: User,
    limit: int = 10,
    skip: int = 0,
) -> list[ReservationResponse]:
    """
    Retrieve user reservation with pagination.
    """
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    _key = current_user.id if current_user.user_type == UserType.GUEST else company_id
    cache_key = f"reservations:{_key}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    guest_id = None
    if current_user.user_type == UserType.GUEST:
        guest_id = current_user.id

    result = await db.execute(
        select(RestaurantReservation)
        .where(
            or_(
                RestaurantReservation.guest_id == guest_id,
                RestaurantReservation.guest_id == company_id,
            )
        )
        .offset(skip)
        .limit(limit)
    )
    reservations = result.unique().scalars().all()
    reservations_data = [
        ReservationCreate.model_validate(reservations).model_dump()
        for reservation in reservations
    ]

    redis_client.set(
        cache_key, json.dumps(reservations_data, default=str), ex=settings.REDIS_EX
    )
    return reservations


async def get_all_company_reservations(
    db: AsyncSession,
    current_user: User,
    limit: int = 10,
    skip: int = 0,
) -> list[ReservationResponse]:
    """
    Retrieve company reservation with pagination.
    """
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    cache_key = f"reservations:{company_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    result = await db.execute(
        select(RestaurantReservation)
        .where(RestaurantReservation.company_id == company_id)
        .offset(skip)
        .limit(limit)
    )
    reservations = result.unique().scalars().all()
    reservations_data = [
        ReservationCreate.model_validate(reservations).model_dump()
        for reservation in reservations
    ]

    redis_client.set(
        cache_key, json.dumps(reservations_data, default=str), ex=settings.REDIS_EX
    )
    return reservations


async def reservation_details(
    reservation_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> ReservationResponse:
    """
    Retrieve company reservation with pagination.
    """
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    cache_key = f"reservations:details:{reservation_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    guest_id = None
    if current_user.user_type == UserType.GUEST:
        guest_id = current_user.id

    result = await db.execute(
        select(RestaurantReservation).where(
            or_(
                RestaurantReservation.company_id == company_id,
                (RestaurantReservation.guest_id == guest_id),
            )
        )
    )
    reservation = result.scalar_one_or_none()
    reservations_data = ReservationCreate.model_validate(reservation).model_dump()

    redis_client.set(
        cache_key, json.dumps(reservations_data, default=str), ex=settings.REDIS_EX
    )
    return reservation


# Update Reservation
# Update Reservation Status
