import json
from operator import or_
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Reservation
from app.schemas.reservation_schema import (
    ReservationCreate,
    ReservationResponse,
    ReservationStatus,
    ReservationUpdate,
)
from app.schemas.user_schema import UserType
from app.utils.utils import check_current_user_id, get_order_payment_link
from app.config.config import settings, redis_client


async def create_reservation(
    db: AsyncSession,
    reservation_data: ReservationCreate,
    current_user: User,
) -> ReservationResponse:
    """Create a new reservation."""
    user_id = check_current_user_id(current_user)
    try:
        # Determine if this is a company-created or guest-created reservation
        is_company_created = current_user.user_type == UserType.COMPANY

        new_reservation = Reservation(
            guest_id=None if is_company_created else current_user.id,
            company_id=current_user.id
            if is_company_created
            else reservation_data.company_id,
            guest_name=reservation_data.guest_name if is_company_created else None,
            guest_email=reservation_data.guest_email if is_company_created else None,
            guest_phone=reservation_data.guest_phone if is_company_created else None,
            arrival_date=reservation_data.arrival_date,
            arrival_time=reservation_data.arrival_time,
            number_of_guests=reservation_data.number_of_guests,
            children=reservation_data.children,
            notes=reservation_data.notes,
            deposit_amount=reservation_data.deposit_amount,
        )

        db.add(new_reservation)
        await db.commit()
        await db.refresh(new_reservation)

        # Generate payment link if deposit is required
        if new_reservation.deposit_amount > 0:
            payment_url = await get_order_payment_link(
                db=db,
                company_id=new_reservation.company_id,
                current_user=current_user,
                _id=new_reservation.id,
                amount=new_reservation.deposit_amount,
            )
            new_reservation.payment_url = payment_url
            await db.commit()
            await db.refresh(new_reservation)

        # Invalidate cache
        company_cache_key = f"reservations:company:{user_id}"
        guest_cache_key = f"reservations:guest:{user_id}"
        redis_client.delete(guest_cache_key)
        redis_client.delete(company_cache_key)

        return new_reservation

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create reservation: {str(e)}",
        )


async def get_user_reservations(
    db: AsyncSession,
    current_user: User,
    limit: int = 10,
    skip: int = 0,
) -> list[ReservationResponse]:
    """
    Retrieve user reservation with pagination.
    """
    user_id = check_current_user_id(current_user)
    company_cache_key = f"reservations:company:{user_id}"
    guest_cache_key = f"reservations:guest:{user_id}"

    cached_reservations = (
        redis_client.get(company_cache_key)
        if current_user.user_type == (UserType.COMPANY or UserType.STAFF)
        else redis_client.get(guest_cache_key)
    )

    if cached_reservations:
        return json.loads(cached_reservations)

    result = await db.execute(
        select(Reservation)
        .where(
            or_(
                Reservation.guest_id == user_id,
                Reservation.company_id == user_id,
            )
        )
        .offset(skip)
        .limit(limit)
    )
    reservations = result.unique().scalars().all()
    reservations_data = [
        ReservationCreate.model_validate(reservation).model_dump()
        for reservation in reservations
    ]

    redis_client.set(
        company_cache_key,
        json.dumps(reservations_data, default=str),
        ex=settings.REDIS_EX,
    )
    redis_client.set(
        guest_cache_key,
        json.dumps(reservations_data, default=str),
        ex=settings.REDIS_EX,
    )
    return reservations


# async def get_all_company_reservations(
#     db: AsyncSession,
#     current_user: User,
#     limit: int = 10,
#     skip: int = 0,
# ) -> list[ReservationResponse]:
#     """
#     Retrieve company reservation with pagination.
#     """
#     company_id = (
#         current_user.id
#         if current_user.user_type == UserType.COMPANY
#         else current_user.company_id
#     )
#     cache_key = f"reservations:{company_id}"
#     cached_items = redis_client.get(cache_key)

#     if cached_items:
#         return json.loads(cached_items)

#     result = await db.execute(
#         select(Reservation)
#         .where(Reservation.company_id == company_id)
#         .offset(skip)
#         .limit(limit)
#     )
#     reservations = result.unique().scalars().all()
#     reservations_data = [
#         ReservationCreate.model_validate(reservation).model_dump()
#         for reservation in reservations
#     ]

#     redis_client.set(
#         cache_key, json.dumps(reservations_data, default=str), ex=settings.REDIS_EX
#     )
#     return reservations


async def reservation_details(
    reservation_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> ReservationResponse:
    """
    Retrieve company reservation with pagination.
    """
    user_id = check_current_user_id(current_user)
    cache_key = f"reservations:details:{reservation_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    result = await db.execute(
        select(Reservation).where(
            or_(
                Reservation.company_id == user_id,
                (Reservation.guest_id == user_id),
            )
        )
    )
    reservation = result.scalar_one_or_none()
    reservations_data = ReservationCreate.model_validate(
        reservation).model_dump()

    redis_client.set(
        cache_key, json.dumps(reservations_data, default=str), ex=settings.REDIS_EX
    )
    return reservation


# Update Reservation
async def update_reservation(
    db: AsyncSession,
    reservation_id: UUID,
    reservation_data: ReservationUpdate,
    current_user: User,
) -> ReservationResponse:
    """Update an existing reservation."""
    user_id = check_current_user_id(current_user)
    query = select(Reservation).where(
        Reservation.id == reservation_id,
        (Reservation.guest_id == user_id) | (
            Reservation.company_id == user_id),
    )
    result = await db.execute(query)
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    # Update fields
    for field, value in reservation_data.model_dump(exclude_unset=True).items():
        setattr(reservation, field, value)

    try:
        await db.commit()
        await db.refresh(reservation)

        # Invalidate cache
        company_cache_key = f"reservations:company:{reservation.company_id}"
        guest_cache_key = f"reservations:guest:{reservation.guest_id}"
        redis_client.delete(company_cache_key)
        redis_client.delete(guest_cache_key)

        return reservation
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update reservation: {str(e)}",
        )
