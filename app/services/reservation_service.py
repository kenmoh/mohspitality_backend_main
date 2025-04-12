import json
from operator import or_
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import User, Reservation
from app.schemas.event_schema import PaymentStatus
from app.schemas.reservation_schema import (
    ReservationCreate,
    ReservationResponse,
    ReservationStatus,
    ReservationUpdate,
)
from app.schemas.user_schema import UserType
from app.utils.utils import get_company_id, get_order_payment_link
from app.config.config import settings, redis_client


async def create_reservation(
    db: AsyncSession,
    reservation_data: ReservationCreate,
    current_user: User,
) -> ReservationResponse:
    """Create a new reservation."""
    company_id = get_company_id(current_user)
    query = (
        select(User)
        .options(joinedload(User.user_profile))
        .where(User.id == current_user.id)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    try:
        # Determine if this is a company-created or guest-created reservation
        is_company_created = current_user.user_type == UserType.COMPANY or current_user.user_type == UserType.STAFF

        new_reservation = Reservation(
            guest_id=None if is_company_created else current_user.id,
            company_id=current_user.id
            if is_company_created
            else reservation_data.company_id,
            guest_name=reservation_data.guest_name if is_company_created else user.user_profile.full_name,
            guest_email=reservation_data.guest_email if is_company_created else user.email,
            guest_phone=reservation_data.guest_phone if is_company_created else user.user_profile.phone_number,
            arrival_date=reservation_data.arrival_date,
            arrival_time=reservation_data.arrival_time,
            number_of_guests=reservation_data.number_of_guests,
            children=reservation_data.children,
            payment_status=PaymentStatus.PENDING,
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
        company_cache_key = f"reservations:company:{company_id}"
        guest_cache_key = f"reservations:guest:{current_user.id}"
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
) -> list[ReservationResponse]:
    """
    Retrieve user reservation with pagination.
    """
    company_id = get_company_id(current_user)

    # Cache key logic
    company_cache_key = f"reservations:company:{company_id}" if company_id else None
    guest_cache_key = f"reservations:guest:{current_user.id}"

    # Check cache based on user type
    if current_user.user_type in (UserType.COMPANY, UserType.STAFF) and company_cache_key:
        cached_reservations = redis_client.get(company_cache_key)
    else:
        cached_reservations = redis_client.get(guest_cache_key)

    if cached_reservations:
        return json.loads(cached_reservations)

    query = select(Reservation)

    if current_user.user_type == UserType.GUEST:
        query = query.where(Reservation.guest_id == current_user.id)
    if current_user.user_type in (UserType.COMPANY, UserType.STAFF):
        query = query.where(Reservation.company_id == company_id)

    result = await db.execute(query)
    reservations = result.unique().scalars().all()

    reservations_data = [reservation.__dict__ for reservation in reservations]

    if company_cache_key:
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


async def reservation_details(
    reservation_id: UUID,
    db: AsyncSession,
    current_user: User,
) -> ReservationResponse:
    """
    Retrieve company reservation with pagination.
    """
    company_id = get_company_id(current_user)
    cache_key = f"reservations:details:{reservation_id}"
    cached_items = redis_client.get(cache_key)

    if cached_items:
        return json.loads(cached_items)

    query = select(Reservation).where(Reservation.id == reservation_id)

    if current_user.user_type == UserType.GUEST:
        query = query.where(Reservation.guest_id == current_user.id)
    if current_user.user_type in (UserType.COMPANY, UserType.STAFF):
        query = query.where(Reservation.company_id == company_id)

    result = await db.execute(query)
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    reservation_data = reservation.__dict__

    redis_client.set(
        cache_key, json.dumps(reservation_data, default=str), ex=settings.REDIS_EX
    )

    return ReservationResponse(**reservation_data)


# Update Reservation
async def update_reservation(
    db: AsyncSession,
    reservation_id: UUID,
    reservation_data: ReservationUpdate,
    current_user: User,
) -> ReservationResponse:
    """Update an existing reservation."""
    company_id = get_company_id(current_user)
    query = select(Reservation).where(
        Reservation.id == reservation_id,
        (Reservation.guest_id == current_user) | (
            Reservation.company_id == company_id),
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


# Update Reservation Status
async def update_reservation_status(
    db: AsyncSession,
    reservation_id: UUID,
    status: ReservationStatus,
    current_user: User,
) -> ReservationResponse:
    """Update the status of an existing reservation."""
    company_id = get_company_id(current_user)
    query = select(Reservation).where(
        Reservation.id == reservation_id,
        (Reservation.guest_id == current_user.id) | (
            Reservation.company_id == company_id),
    )
    result = await db.execute(query)
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    # Update status
    reservation.status = status

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
            detail=f"Failed to update reservation status: {str(e)}",
        )
