from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import (
    EventBooking,
    EventMenuItem,
    MeetingRoom,
    SeatArrangement,
    User,
)
from app.schemas.event_schema import (
    EventBookingCreate,
    EventBookingResponse,
    EventBookingUpdate,
    EventMenuItemCreate,
    EventMenuItemResponse,
    EventMenuItemUpdate,
    EventStatus,
    MeetingRoomCreate,
    MeetingRoomResponse,
    MeetingRoomUpdate,
    SeatArrangementCreate,
    SeatArrangementResponse,
    SeatArrangementUpdate,
)

from app.schemas.user_schema import UserType
from app.config.config import settings, redis_client


async def create_meeting_room(
    room_data: MeetingRoomCreate, db: AsyncSession, current_user: User
) -> MeetingRoomResponse:
    """Create a new meeting room. Only company users can create rooms."""

    if current_user.user_type == UserType.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company users can create meeting rooms",
        )

    try:
        new_room = MeetingRoom(company_id=current_user.id, **room_data.model_dump())

        db.add(new_room)
        await db.commit()
        await db.refresh(new_room)

        return MeetingRoomResponse.model_validate(new_room)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create meeting room: {str(e)}",
        )


async def get_meeting_room(
    room_id: int, db: AsyncSession, current_user: User
) -> MeetingRoomResponse:
    """Get a single meeting room by ID."""
    query = select(MeetingRoom).where(MeetingRoom.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting room not found"
        )

    return MeetingRoomResponse.model_validate(room)


async def get_company_meeting_rooms(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
    is_available: bool = None,
) -> list[MeetingRoomResponse]:
    """Get all meeting rooms for a company with optional filtering."""
    # Check cache first
    cache_key = f"rooms:company:{current_user.id}:skip:{skip}:limit:{limit}:available:{is_available}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return [MeetingRoomResponse.model_validate(item) for item in cached_data]

    query = (
        select(MeetingRoom)
        .where(MeetingRoom.company_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )

    if is_available is not None:
        query = query.where(MeetingRoom.is_available == is_available)

    result = await db.execute(query)
    rooms = result.scalars().all()

    # Cache the results
    response = [MeetingRoomResponse.model_validate(r) for r in rooms]
    redis_client.set(
        cache_key, [r.model_dump() for r in response], ex=settings.REDIS_EX
    )

    return response


async def update_meeting_room(
    room_id: int, room_data: MeetingRoomUpdate, db: AsyncSession, current_user: User
) -> MeetingRoomResponse:
    """Update an existing meeting room."""
    query = select(MeetingRoom).where(
        MeetingRoom.id == room_id, MeetingRoom.company_id == current_user.id
    )
    result = await db.execute(query)
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting room not found"
        )

    # Update fields
    for field, value in room_data.model_dump(exclude_unset=True).items():
        setattr(room, field, value)

    try:
        await db.commit()
        await db.refresh(room)

        # Invalidate cache
        cache_key = f"rooms:company:{current_user.id}"
        redis_client.delete(cache_key)

        return MeetingRoomResponse.model_validate(room)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update meeting room: {str(e)}",
        )


async def delete_meeting_room(
    room_id: int, db: AsyncSession, current_user: User
) -> None:
    """Delete a meeting room."""
    query = select(MeetingRoom).where(
        MeetingRoom.id == room_id, MeetingRoom.company_id == current_user.id
    )
    result = await db.execute(query)
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting room not found"
        )

    try:
        await db.delete(room)
        await db.commit()

        # Invalidate cache
        cache_key = f"rooms:company:{current_user.id}"
        redis_client.delete(cache_key)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete meeting room: {str(e)}",
        )


async def create_seat_arrangement(
    arrangement_data: SeatArrangementCreate, db: AsyncSession, current_user: User
) -> SeatArrangementResponse:
    """Create a new seating arrangement. Only company users can create arrangements."""

    if current_user.user_type == UserType.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company users can create seating arrangements",
        )

    try:
        new_arrangement = SeatArrangement(
            company_id=current_user.id, **arrangement_data.model_dump()
        )

        db.add(new_arrangement)
        await db.commit()
        await db.refresh(new_arrangement)

        return SeatArrangementResponse.model_validate(new_arrangement)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create seating arrangement: {str(e)}",
        )


async def get_seat_arrangement(
    arrangement_id: int, db: AsyncSession, current_user: User
) -> SeatArrangementResponse:
    """Get a single seat arrangement by ID."""
    query = select(SeatArrangement).where(SeatArrangement.id == arrangement_id)
    result = await db.execute(query)
    arrangement = result.scalar_one_or_none()

    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seat arrangement not found"
        )

    return SeatArrangementResponse.model_validate(arrangement)


async def get_company_seat_arrangements(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
    is_available: bool = None,
) -> list[SeatArrangementResponse]:
    """Get all seat arrangements for a company with optional filtering."""
    cache_key = f"arrangements:company:{current_user.id}:skip:{skip}:limit:{limit}:available:{is_available}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return [SeatArrangementResponse.model_validate(item) for item in cached_data]

    query = (
        select(SeatArrangement)
        .where(SeatArrangement.company_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )

    if is_available is not None:
        query = query.where(SeatArrangement.is_available == is_available)

    result = await db.execute(query)
    arrangements = result.scalars().all()

    response = [SeatArrangementResponse.model_validate(r) for r in arrangements]

    redis_client.set(
        cache_key, [r.model_dump() for r in response], ex=settings.REDIS_EX
    )

    return response


async def update_seat_arrangement(
    arrangement_id: int,
    arrangement_data: SeatArrangementUpdate,
    db: AsyncSession,
    current_user: User,
) -> SeatArrangementResponse:
    """Update an existing seat arrangement."""
    query = select(SeatArrangement).where(
        SeatArrangement.id == arrangement_id,
        SeatArrangement.company_id == current_user.id,
    )
    result = await db.execute(query)
    arrangement = result.scalar_one_or_none()

    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seat arrangement not found"
        )

    # Update fields
    for field, value in arrangement_data.model_dump(exclude_unset=True).items():
        setattr(arrangement, field, value)

    try:
        await db.commit()
        await db.refresh(arrangement)

        # Invalidate cache
        cache_key = f"arrangements:company:{current_user.id}"
        redis_client.delete(cache_key)

        return SeatArrangementResponse.model_validate(arrangement)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update seat arrangement: {str(e)}",
        )


async def delete_seat_arrangement(
    arrangement_id: int, db: AsyncSession, current_user: User
) -> None:
    """Delete a seat arrangement."""
    query = select(SeatArrangement).where(
        SeatArrangement.id == arrangement_id,
        SeatArrangement.company_id == current_user.id,
    )
    result = await db.execute(query)
    arrangement = result.scalar_one_or_none()

    if not arrangement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seat arrangement not found"
        )

    try:
        await db.delete(arrangement)
        await db.commit()

        # Invalidate cache
        cache_key = f"arrangements:company:{current_user.id}"
        redis_client.delete(cache_key)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete seat arrangement: {str(e)}",
        )


async def create_event_booking(
    booking_data: EventBookingCreate, db: AsyncSession, current_user: User
) -> EventBookingResponse:
    """
    Create a new event booking.
    Both company users and guests can create bookings.
    """
    try:
        # Determine if this is a company-created or guest-created booking
        is_company_created = current_user.user_type == UserType.COMPANY

        new_booking = EventBooking(
            guest_id=None if is_company_created else current_user.id,
            company_id=current_user.id
            if is_company_created
            else booking_data.company_id,
            guest_name=booking_data.guest_name if is_company_created else None,
            guest_email=booking_data.guest_email if is_company_created else None,
            guest_phone=booking_data.guest_phone if is_company_created else None,
            **booking_data.model_dump(
                exclude={"guest_name", "guest_email", "guest_phone"}
            ),
        )

        # Add menu items if specified
        if booking_data.menu_item_ids:
            menu_items = await db.execute(
                select(EventMenuItem).where(
                    EventMenuItem.id.in_(booking_data.menu_item_ids)
                )
            )
            new_booking.menu_items = menu_items.scalars().all()

        db.add(new_booking)
        await db.commit()
        await db.refresh(new_booking)

        return EventBookingResponse.model_validate(new_booking)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create event booking: {str(e)}",
        )


async def get_event_booking(
    booking_id: UUID, db: AsyncSession, current_user: User
) -> EventBookingResponse:
    """Get a single event booking by ID."""
    query = select(EventBooking).where(
        EventBooking.id == booking_id,
        or_(
            EventBooking.guest_id == current_user.id,
            EventBooking.company_id == current_user.id,
        ),
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event booking not found"
        )

    return EventBookingResponse.model_validate(booking)


async def get_bookings(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
    status: EventStatus = None,
) -> list[EventBookingResponse]:
    """Get all bookings for a user (either as guest or company)."""
    cache_key = (
        f"bookings:user:{current_user.id}:status:{status}:skip:{skip}:limit:{limit}"
    )
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return [EventBookingResponse.model_validate(item) for item in cached_data]

    query = (
        select(EventBooking)
        .where(
            or_(
                EventBooking.guest_id == current_user.id,
                EventBooking.company_id == current_user.id,
            )
        )
        .offset(skip)
        .limit(limit)
    )

    if status:
        query = query.where(EventBooking.status == status)

    result = await db.execute(query)
    bookings = result.scalars().all()

    response = [EventBookingResponse.model_validate(b) for b in bookings]

    redis_client.set(
        cache_key, [r.model_dump() for r in response], ex=settings.REDIS_EX
    )

    return response


async def update_event_booking(
    booking_id: UUID,
    booking_data: EventBookingUpdate,
    db: AsyncSession,
    current_user: User,
) -> EventBookingResponse:
    """Update an existing event booking."""
    query = select(EventBooking).where(
        EventBooking.id == booking_id,
        or_(
            EventBooking.guest_id == current_user.id,
            EventBooking.company_id == current_user.id,
        ),
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event booking not found"
        )

    # Update fields
    update_data = booking_data.model_dump(exclude_unset=True)

    # Handle menu items separately if they're being updated
    menu_item_ids = update_data.pop("menu_item_ids", None)
    if menu_item_ids is not None:
        menu_items = await db.execute(
            select(EventMenuItem).where(EventMenuItem.id.in_(menu_item_ids))
        )
        booking.menu_items = menu_items.scalars().all()

    # Update other fields
    for field, value in update_data.items():
        setattr(booking, field, value)

    try:
        await db.commit()
        await db.refresh(booking)

        # Invalidate cache
        cache_key = f"bookings:{booking.company_id}"
        redis_client.delete(cache_key)

        return EventBookingResponse.model_validate(booking)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update event booking: {str(e)}",
        )


async def cancel_event_booking(
    booking_id: UUID, db: AsyncSession, current_user: User
) -> EventBookingResponse:
    """Cancel an event booking."""
    query = select(EventBooking).where(
        EventBooking.id == booking_id,
        or_(
            EventBooking.guest_id == current_user.id,
            EventBooking.company_id == current_user.id,
        ),
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event booking not found"
        )

    if booking.status == EventStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
        )

    booking.status = EventStatus.CANCELLED

    try:
        await db.commit()
        await db.refresh(booking)

        # Invalidate cache
        cache_key = f"bookings:{booking.company_id}"
        redis_client.delete(cache_key)

        return EventBookingResponse.model_validate(booking)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel event booking: {str(e)}",
        )


async def create_menu_item(
    item_data: EventMenuItemCreate, db: AsyncSession, current_user: User
) -> EventMenuItemResponse:
    """Create a new menu item. Only company users can create menu items."""

    if current_user.user_type != UserType.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company users can create menu items",
        )

    try:
        new_item = EventMenuItem(company_id=current_user.id, **item_data.model_dump())

        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)

        return EventMenuItemResponse.model_validate(new_item)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create menu item: {str(e)}",
        )


async def get_menu_item(
    item_id: int, db: AsyncSession, current_user: User
) -> EventMenuItemResponse:
    """Get a single menu item by ID."""
    query = select(EventMenuItem).where(EventMenuItem.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
        )

    return EventMenuItemResponse.model_validate(item)


async def get_company_menu_items(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
    is_available: bool = None,
    category: str = None,
) -> list[EventMenuItemResponse]:
    """Get all menu items for a company with optional filtering."""
    cache_key = f"menu:company:{current_user.id}:skip:{skip}:limit:{limit}:available:{is_available}:category:{category}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        return [EventMenuItemResponse.model_validate(item) for item in cached_data]

    query = (
        select(EventMenuItem)
        .where(EventMenuItem.company_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )

    if is_available is not None:
        query = query.where(EventMenuItem.is_available == is_available)

    if category:
        query = query.where(EventMenuItem.category == category)

    result = await db.execute(query)
    items = result.scalars().all()

    response = [EventMenuItemResponse.model_validate(r) for r in items]

    redis_client.set(
        cache_key, [r.model_dump() for r in response], ex=settings.REDIS_EX
    )

    return response


async def update_menu_item(
    item_id: int, item_data: EventMenuItemUpdate, db: AsyncSession, current_user: User
) -> EventMenuItemResponse:
    """Update an existing menu item."""
    query = select(EventMenuItem).where(
        EventMenuItem.id == item_id, EventMenuItem.company_id == current_user.id
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
        )

    # Update fields
    for field, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    try:
        await db.commit()
        await db.refresh(item)

        # Invalidate cache
        cache_key = f"menu:company:{current_user.id}"
        redis_client.delete(cache_key)

        return EventMenuItemResponse.model_validate(item)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update menu item: {str(e)}",
        )


async def delete_menu_item(item_id: int, db: AsyncSession, current_user: User) -> None:
    """Delete a menu item."""
    query = select(EventMenuItem).where(
        EventMenuItem.id == item_id, EventMenuItem.company_id == current_user.id
    )
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found"
        )

    try:
        await db.delete(item)
        await db.commit()

        # Invalidate cache
        cache_key = f"menu:company:{current_user.id}"
        redis_client.delete(cache_key)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete menu item: {str(e)}",
        )
