from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
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

from app.services import event_service


router = APIRouter(prefix="/api/events", tags=["Events"])

# Meeting Room Routes


@router.post("/rooms", status_code=status.HTTP_201_CREATED)
async def create_meeting_room(
    room_data: MeetingRoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeetingRoomResponse:
    return await event_service.create_meeting_room(room_data, db, current_user)


@router.get("/company-rooms", status_code=status.HTTP_200_OK)
async def get_company_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MeetingRoomResponse]:
    return await event_service.get_company_meeting_rooms(db, current_user)


@router.get("/{room_id}/rooms", status_code=status.HTTP_200_OK)
async def get_meeting_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeetingRoomResponse:
    return await event_service.get_meeting_room(room_id, db, current_user)


@router.put("/{room_id}/rooms", status_code=status.HTTP_202_ACCEPTED)
async def update_meeting_room(
    room_id: int,
    room_data: MeetingRoomUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeetingRoomResponse:
    return await event_service.update_meeting_room(room_id, room_data, db, current_user)


@router.delete("/{room_id}/rooms", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await event_service.delete_meeting_room(room_id, db, current_user)


# Seat Arrangement Routes


@router.post("/arrangements", status_code=status.HTTP_201_CREATED)
async def create_seat_arrangement(
    arrangement_data: SeatArrangementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeatArrangementResponse:
    return await event_service.create_seat_arrangement(
        arrangement_data, db, current_user
    )


@router.get("/{arrangement_id}/arrangements", status_code=status.HTTP_200_OK)
async def get_seat_arrangement(
    arrangement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeatArrangementResponse:
    return await event_service.get_seat_arrangement(arrangement_id, db, current_user)


@router.get("/company-seat-arrangements", status_code=status.HTTP_200_OK)
async def get_company_arrangements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SeatArrangementResponse]:
    return await event_service.get_company_seat_arrangements(db, current_user)


@router.delete("/{arrangement_id}/arrangements", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat_arrangement(
    arrangement_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await event_service.delete_seat_arrangement(arrangement_id, db, current_user)


# Event Menu Item Routes


@router.post("/menu-items", status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    item_data: EventMenuItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventMenuItemResponse:
    return await event_service.create_menu_item(item_data, db, current_user)


@router.get("/{item_id}/menu-items", status_code=status.HTTP_200_OK)
async def get_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventMenuItemResponse:
    return await event_service.get_menu_item(item_id, db, current_user)


@router.get("/company-menu-items", status_code=status.HTTP_200_OK)
async def get_company_menu_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventMenuItemResponse]:
    return await event_service.get_company_menu_items(db, current_user)


@router.put("/{item_id}/menu-items", status_code=status.HTTP_202_ACCEPTED)
async def update_menu_item(
    item_id: int,
    item_data: EventMenuItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventMenuItemResponse:
    return await event_service.update_menu_item(item_id, item_data, db, current_user)


@router.delete("/{item_id}/menu-items", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await event_service.delete_menu_item(item_id, db, current_user)


# Event Booking Routes


@router.post("/{company_id}/bookings", status_code=status.HTTP_201_CREATED)
async def create_event_booking(
    company_id: UUID,
    booking_data: EventBookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventBookingResponse:
    return await event_service.create_event_booking(
        booking_data=booking_data,
        company_id=company_id,
        db=db,
        current_user=current_user,
    )


@router.get("/{booking_id}/bookings", status_code=status.HTTP_200_OK)
async def get_event_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventBookingResponse:
    return await event_service.get_event_booking(booking_id, db, current_user)


@router.get("/bookings", status_code=status.HTTP_200_OK)
async def get_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1),
    status: Optional[EventStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EventBookingResponse]:
    return await event_service.get_bookings(db, current_user, skip, limit, status)


@router.put("/{booking_id}/bookings", status_code=status.HTTP_202_ACCEPTED)
async def update_event_booking(
    booking_id: UUID,
    booking_data: EventBookingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventBookingResponse:
    return await event_service.update_event_booking(
        booking_id, booking_data, db, current_user
    )


@router.post("/bookings/{booking_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_event_booking(
    booking_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventBookingResponse:
    return await event_service.cancel_event_booking(booking_id, db, current_user)


@router.get("/company/{company_id}/menu-items/selection")
async def get_menu_items_selection(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[MenuItemSelection]:
    return await event_service.get_menu_items_for_selection(db, company_id)


@router.get("/company/{company_id}/rooms/selection")
async def get_rooms_selection(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[RoomSelection]:
    return await event_service.get_rooms_for_selection(db, company_id)


@router.get("/company/{company_id}/arrangements/selection")
async def get_arrangements_selection(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[SeatArrangementSelection]:
    return await event_service.get_arrangements_for_selection(db, company_id)
