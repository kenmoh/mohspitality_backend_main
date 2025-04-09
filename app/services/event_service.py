from datetime import date, time, datetime
from decimal import Decimal

import json
from uuid import UUID
from asyncpg import UniqueViolationError
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from sqlalchemy import or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    EventBooking,
    EventMenuItem,
    MeetingRoom,
    SeatArrangement,
    User,
    UserProfile,
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
    MenuItemSelection,
    RoomSelection,
    SeatArrangementCreate,
    SeatArrangementResponse,
    SeatArrangementSelection,
    SeatArrangementUpdate,
)

from app.schemas.user_schema import UserType
from app.config.config import settings, redis_client
from app.utils.utils import check_current_user_id


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
        new_room = MeetingRoom(company_id=current_user.id,
                               updated_at=datetime.now(), **room_data.model_dump())

        db.add(new_room)
        await db.commit()
        await db.refresh(new_room)

        return new_room
    except IntegrityError as e:
        await db.rollback()
        error_message = str(e.orig)
        if "unique constraint" in error_message.lower() and "room_name" in error_message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A room named '{room_data.name}' already exists for your company"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while creating the room"
        )

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

    user_id = check_current_user_id(current_user)
    cache_key = f"rooms:details:company:{user_id}"
    cached_data = redis_client.get(cache_key)

    # Check cache first
    if cached_data:
        print('==================FROM CACHE==================ROOOM', cached_data)
        return json.loads(cached_data)

    query = select(MeetingRoom).where(MeetingRoom.id == room_id)
    result = await db.execute(query)
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting room not found"
        )
    room_data = MeetingRoomResponse.model_validate(room).model_dump()

    # Cache the results
    redis_client.set(
        cache_key, json.dumps(room_data, default=str), ex=settings.REDIS_EX
    )

    return room


async def get_company_meeting_rooms(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 20,
    is_available: bool = None,
) -> list[MeetingRoomResponse]:
    """Get all meeting rooms for a company with optional filtering."""
    # Check cache first
    user_id = check_current_user_id(current_user)
    cache_key = f"rooms:company:{user_id}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        data = json.loads(cached_data)
        return [MeetingRoomResponse.model_validate(room) for room in data]

    query = (
        select(MeetingRoom)
        .where(MeetingRoom.company_id == user_id)
        .offset(skip)
        .limit(limit)
    )

    if is_available is not None:
        query = query.where(MeetingRoom.is_available == is_available)

    result = await db.execute(query)
    rooms = result.unique().scalars().all()
    rooms_dict = [room.__dict__ for room in rooms]

    rooms_data = [
        MeetingRoomResponse.model_validate(room_dict).model_dump() for room_dict in rooms_dict
    ]

    # Cache the results
    redis_client.set(
        cache_key, json.dumps(rooms_data, default=str), ex=settings.REDIS_EX
    )

    return rooms


async def update_meeting_room(
    room_id: int, room_data: MeetingRoomUpdate, db: AsyncSession, current_user: User
) -> MeetingRoomResponse:
    """Update an existing meeting room."""

    company_id = check_current_user_id(current_user)
    query = select(MeetingRoom).where(
        MeetingRoom.id == room_id, MeetingRoom.company_id == company_id
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

    response = [SeatArrangementResponse.model_validate(
        r) for r in arrangements]

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


# async def create_event_booking(
#     company_id: UUID,
#     booking_data: EventBookingCreate, db: AsyncSession, current_user: User
# ) -> EventBookingResponse:
#     """
#     Create a new event booking.
#     Both company users and guests can create bookings.
#     """
#     query = select(UserProfile.full_name).where(
#         UserProfile.user_id == current_user.id, current_user.user_type == UserType.STAFF
#     )
#     result = await db.execute(query)
#     staff_name = result.scalar_one_or_none()
#     try:
#         # Determine if this is a company-created or guest-created booking
#         is_company_created = current_user.user_type in [
#             UserType.COMPANY, UserType.STAFF]
#         booking_company_id = (
#             current_user.id
#             if current_user.user_type == UserType.COMPANY
#             else current_user.company_id if current_user.user_type == UserType.STAFF
#             else company_id
#         )

#         new_booking = EventBooking(
#             guest_id=None if is_company_created else current_user.id,
#             company_id=booking_company_id,
#             staff_name=staff_name if is_company_created else None,
#             guest_name=booking_data.guest_name if is_company_created else None,
#             guest_email=booking_data.guest_email if is_company_created else None,
#             guest_phone=booking_data.guest_phone if is_company_created else None,
#             **booking_data.model_dump(
#                 exclude={"guest_name", "guest_email", "guest_phone"}
#             ),
#         )

#         # Add menu items if specified
#         if booking_data.menu_item_ids:
#             menu_items = await db.execute(
#                 select(EventMenuItem).where(
#                     EventMenuItem.id.in_(booking_data.menu_item_ids)
#                 )
#             )
#             new_booking.menu_items = menu_items.scalars().all()

#         db.add(new_booking)
#         await db.commit()
#         await db.refresh(new_booking)

#         return EventBookingResponse.model_validate(new_booking)

#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Failed to create event booking: {str(e)}",
#         )

async def create_event_booking(
    company_id: UUID,
    booking_data: EventBookingCreate,
    db: AsyncSession,
    current_user: User
) -> EventBookingResponse:
    """
    Create a new event booking.
    Both company users and guests can create bookings.
    """
    # Get staff name if applicable
    query = select(UserProfile.full_name).where(
        UserProfile.user_id == current_user.id,
        current_user.user_type == UserType.STAFF
    )
    result = await db.execute(query)
    staff_name = result.scalar_one_or_none()

    try:
        # Determine booking ownership
        is_company_created = current_user.user_type in [
            UserType.COMPANY, UserType.STAFF]
        booking_company_id = (
            current_user.id
            if current_user.user_type == UserType.COMPANY
            else current_user.company_id if current_user.user_type == UserType.STAFF
            else company_id
        )

        # Validate selections
        if booking_data.selected_room:
            rooms = await get_rooms_for_selection(db, booking_company_id)
            if not any(room.id == booking_data.selected_room for room in rooms):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected room not found or not available"
                )

        if booking_data.selected_arrangement:
            arrangements = await get_arrangements_for_selection(db, booking_company_id)
            if not any(a.id == booking_data.selected_arrangement for a in arrangements):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected arrangement not found or not available"
                )

        if booking_data.room_name:
            room_query = select(MeetingRoom).where(
                and_(
                    MeetingRoom.name == booking_data.room_name,
                    MeetingRoom.company_id == booking_company_id,
                    MeetingRoom.is_available == True
                )
            )
            room = await db.execute(room_query)
            room = room.scalar_one_or_none()

            if not room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Meeting room '{booking_data.room_name}' not found or not available"
                )

            # Check room availability for the requested time
            is_available = await is_room_available(
                db=db,
                room_id=room.id,
                arrival_date=booking_data.arrival_date,
                arrival_time=booking_data.arrival_time,
                end_time=booking_data.end_time,
                end_date=booking_data.end_date
            )

            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Meeting room '{booking_data.room_name}' is not available for the selected time slot"
                )

        # Calculate total amount including menu items
        total_amount = Decimal("0.00")
        menu_items = []
        if booking_data.selected_menu_items:
            available_items = await get_menu_items_for_selection(db, booking_company_id)
            menu_items = [
                item for item in available_items
                if item.id in booking_data.selected_menu_items
            ]
            if len(menu_items) != len(booking_data.selected_menu_items):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some selected menu items are not available"
                )
            total_amount = sum(item.price for item in menu_items)

        # Create booking
        new_booking = EventBooking(
            guest_id=None if is_company_created else current_user.id,
            company_id=booking_company_id,
            staff_name=staff_name if is_company_created else None,
            guest_name=booking_data.guest_name if is_company_created else None,
            guest_email=booking_data.guest_email if is_company_created else None,
            guest_phone=booking_data.guest_phone if is_company_created else None,
            meeting_room_id=booking_data.selected_room,
            seat_arrangement_id=booking_data.selected_arrangement,
            total_amount=total_amount,
            **booking_data.model_dump(
                exclude={
                    "guest_name", "guest_email", "guest_phone",
                    "selected_menu_items", "selected_room", "selected_arrangement"
                }
            ),
        )

        # Add selected menu items
        if menu_items:
            menu_item_records = await db.execute(
                select(EventMenuItem).where(
                    EventMenuItem.id.in_([item.id for item in menu_items])
                )
            )
            new_booking.menu_items = menu_item_records.scalars().all()

        db.add(new_booking)
        await db.commit()
        await db.refresh(new_booking)

        # Invalidate cache
        cache_key = f"bookings:company:{booking_company_id}"
        redis_client.delete(cache_key)

        return EventBookingResponse.model_validate(new_booking)

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create event booking: {str(e)}"
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


# async def update_event_booking(
#     booking_id: UUID,
#     booking_data: EventBookingUpdate,
#     db: AsyncSession,
#     current_user: User,
# ) -> EventBookingResponse:
#     """Update an existing event booking."""
#     query = select(EventBooking).where(
#         EventBooking.id == booking_id,
#         or_(
#             EventBooking.guest_id == current_user.id,
#             EventBooking.company_id == current_user.id,
#         ),
#     )
#     result = await db.execute(query)
#     booking = result.scalar_one_or_none()

#     if not booking:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Event booking not found"
#         )

#     # Update fields
#     update_data = booking_data.model_dump(exclude_unset=True)

#     # Handle menu items separately if they're being updated
#     menu_item_ids = update_data.pop("menu_item_ids", None)
#     if menu_item_ids is not None:
#         menu_items = await db.execute(
#             select(EventMenuItem).where(EventMenuItem.id.in_(menu_item_ids))
#         )
#         booking.menu_items = menu_items.scalars().all()

#     # Update other fields
#     for field, value in update_data.items():
#         setattr(booking, field, value)

#     try:
#         await db.commit()
#         await db.refresh(booking)

#         # Invalidate cache
#         cache_key = f"bookings:{booking.company_id}"
#         redis_client.delete(cache_key)

#         return EventBookingResponse.model_validate(booking)
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Failed to update event booking: {str(e)}",
#         )

async def update_event_booking(
    booking_id: UUID,
    booking_data: EventBookingUpdate,
    db: AsyncSession,
    current_user: User,
) -> EventBookingResponse:
    """Update an existing event booking."""

    user_id = check_current_user_id(current_user)
    query = select(EventBooking).where(
        EventBooking.id == booking_id,
        or_(
            EventBooking.guest_id == user_id,
            EventBooking.company_id == user_id,
        ),
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event booking not found"
        )

    # Check room availability if room or time is being updated
    if any([
        booking_data.room_name,
        booking_data.arrival_date,
        booking_data.arrival_time,
        booking_data.end_time,
        booking_data.end_date
    ]):
        # Get room ID (either from update data or existing booking)
        if booking_data.room_name:
            room_query = select(MeetingRoom).where(
                and_(
                    MeetingRoom.name == booking_data.room_name,
                    MeetingRoom.company_id == booking.company_id,
                    MeetingRoom.is_available == True
                )
            )
            room = await db.execute(room_query)
            room = room.scalar_one_or_none()

            if not room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Meeting room '{booking_data.room_name}' not found or not available"
                )
            room_id = room.id
        else:
            room_id = booking.meeting_room_id

        # Check availability using either new or existing dates/times
        is_available = await is_room_available(
            db=db,
            room_id=room_id,
            arrival_date=booking_data.arrival_date or booking.arrival_date,
            arrival_time=booking_data.arrival_time or booking.arrival_time,
            end_time=booking_data.end_time or booking.end_time,
            end_date=booking_data.end_date or booking.end_date,
            exclude_booking_id=booking_id  # Exclude current booking from check
        )

        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting room is not available for the selected time slot"
            )

    # Update fields
    update_data = booking_data.model_dump(exclude_unset=True)

    # Handle menu items separately if they're being updated
    menu_item_ids = update_data.pop("menu_item_ids", None)
    if menu_item_ids is not None:
        menu_items = await db.execute(
            select(EventMenuItem).where(
                EventMenuItem.id.in_(menu_item_ids)
            )
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
        new_item = EventMenuItem(
            company_id=current_user.id, **item_data.model_dump())

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


async def get_menu_items_for_selection(
    db: AsyncSession,
    company_id: UUID,
) -> list[MenuItemSelection]:
    """Get available menu items for dropdown selection."""
    query = select(EventMenuItem).where(
        EventMenuItem.company_id == company_id,
        EventMenuItem.is_available == True
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        MenuItemSelection(
            id=item.id,
            name=item.name,
            price=item.price
        ) for item in items
    ]


async def get_rooms_for_selection(
    db: AsyncSession,
    company_id: UUID,
) -> list[RoomSelection]:
    """Get available rooms for dropdown selection."""
    query = select(MeetingRoom).where(
        MeetingRoom.company_id == company_id,
        MeetingRoom.is_available == True
    )
    result = await db.execute(query)
    rooms = result.scalars().all()

    return [
        RoomSelection(
            id=room.id,
            name=room.name,
            capacity=room.capacity
        ) for room in rooms
    ]


async def get_arrangements_for_selection(
    db: AsyncSession,
    company_id: UUID,
) -> list[SeatArrangementSelection]:
    """Get available seating arrangements for dropdown selection."""
    query = select(SeatArrangement).where(
        SeatArrangement.company_id == company_id,
        SeatArrangement.is_available == True
    )
    result = await db.execute(query)
    arrangements = result.scalars().all()

    return [
        SeatArrangementSelection(
            id=arr.id,
            name=arr.name,
            capacity=arr.capacity
        ) for arr in arrangements
    ]


async def is_room_available(
    db: AsyncSession,
    room_id: int,
    arrival_date: date,
    arrival_time: time,
    end_time: time,
    end_date: date | None = None,
    exclude_booking_id: UUID | None = None
) -> bool:
    """
    Check if a meeting room is available for the specified time period.
    Handles both same-day and multi-day events.
    Returns True if room is available, False otherwise.
    """
    # If end_date is not provided, assume same-day event
    end_date = end_date or arrival_date

    # Create datetime objects for comparison
    arrival_dt = datetime.combine(arrival_date, arrival_time)
    end_dt = datetime.combine(end_date, end_time)

    # Validate that end datetime is after start datetime
    if end_dt <= arrival_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )

    # Query existing bookings that might overlap
    # query = (
    #     select(EventBooking)
    #     .where(
    #         EventBooking.meeting_room_id == room_id,
    #         EventBooking.status != EventStatus.CANCELLED,
    #         # Check for date range overlap
    #         or_(
    #             and_(
    #                 EventBooking.arrival_date >= arrival_date,
    #                 EventBooking.arrival_date <= end_date
    #             ),
    #             and_(
    #                 EventBooking.end_date >= arrival_date,
    #                 EventBooking.end_date <= end_date
    #             ) if hasattr(EventBooking, 'end_date') else False
    #         )
    #     )
    # )
    # Query existing bookings that might overlap
    query = (
        select(EventBooking)
        .where(
            EventBooking.meeting_room_id == room_id,
            EventBooking.status != EventStatus.CANCELLED,
            # Check for any kind of date/time overlap using standard overlap logic:
            # Event A doesn't end before Event B starts AND Event A doesn't start after Event B ends
            and_(
                or_(
                    # Same day overlap
                    and_(
                        EventBooking.arrival_date == arrival_date,
                        EventBooking.arrival_time < end_time,
                        EventBooking.end_time > arrival_time
                    ),
                    # Multi-day overlap
                    and_(
                        # Event starts during the requested period
                        and_(
                            EventBooking.arrival_date >= arrival_date,
                            EventBooking.arrival_date <= end_date
                        ),
                        # OR event ends during the requested period
                        or_(
                            and_(
                                EventBooking.end_date >= arrival_date,
                                EventBooking.end_date <= end_date
                            ),
                            # OR event spans the entire requested period
                            and_(
                                EventBooking.arrival_date <= arrival_date,
                                EventBooking.end_date >= end_date
                            )
                        )
                    )
                )
            )
        )
    )

    if exclude_booking_id:
        query = query.where(EventBooking.id != exclude_booking_id)

    result = await db.execute(query)
    existing_bookings = result.scalars().all()

    # Check for time conflicts
    for booking in existing_bookings:
        booking_start = datetime.combine(
            booking.arrival_date, booking.arrival_time)
        booking_end = datetime.combine(
            booking.end_date if hasattr(
                booking, 'end_date') else booking.arrival_date,
            booking.end_time
        )

        # Check if there's any overlap
        if (
            (arrival_dt <= booking_end and end_dt >= booking_start) or
            (booking_start <= end_dt and booking_end >= arrival_dt)
        ):
            return False

    return True
