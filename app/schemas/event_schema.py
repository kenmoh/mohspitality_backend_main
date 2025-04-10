from enum import Enum
from datetime import datetime, date, time
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class EventStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class MenuItemSelection(BaseModel):
    id: int
    name: str
    price: Decimal


class RoomSelection(BaseModel):
    id: int
    name: str
    capacity: int


class SeatArrangementSelection(BaseModel):
    id: int
    name: str
    capacity: int


class MeetingRoomBase(BaseModel):
    name: str
    capacity: int
    price: Decimal
    amenities: List[str] = []
    image_url: Optional[str] = None


class MeetingRoomCreate(MeetingRoomBase):
    pass


class MeetingRoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = None
    price: Optional[Decimal] = None
    amenities: Optional[List[str]] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None


class MeetingRoomResponse(MeetingRoomBase):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class SeatArrangementBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: str


class SeatArrangementCreate(SeatArrangementBase):
    pass


class SeatArrangementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class SeatArrangementResponse(SeatArrangementBase):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class EventMenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: str
    is_available: bool = True
    dietary_info: Optional[str] = None
    serving_size: Optional[int] = None


class EventMenuItemCreate(EventMenuItemBase):
    pass


class EventMenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None
    dietary_info: Optional[str] = None
    serving_size: Optional[int] = None


class EventMenuItemResponse(EventMenuItemBase):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class EventMenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: str
    is_available: bool = True
    dietary_info: Optional[str] = None
    serving_size: Optional[int] = None


class EventMenuItemCreate(EventMenuItemBase):
    pass


class EventMenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None
    dietary_info: Optional[str] = None
    serving_size: Optional[int] = None


class EventMenuItemResponse(EventMenuItemBase):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class EventBookingBase(BaseModel):
    arrival_date: date
    arrival_time: time
    end_date: Optional[date] = None
    end_time: time
    event_type: str
    event_theme: Optional[str] = None
    number_of_guests: int
    event_duration: int
    requires_catering: bool = True
    requires_decoration: bool = False
    requires_equipment: bool = False
    equipment_needed: Optional[List[str]] = None
    special_requests: Optional[str] = None
    notes: Optional[str] = None
    catering_size: Optional[int] = None


# class EventBookingCreate(EventBookingBase):
#     meeting_room_id: Optional[int] = None
#     seat_arrangement_id: Optional[int] = None
#     menu_item_ids: Optional[List[int]] = None
#     guest_name: Optional[str] = None
#     guest_email: Optional[EmailStr] = None
#     guest_phone: Optional[str] = None
#     deposit_amount: Optional[Decimal] = None

class EventBookingCreate(EventBookingBase):
    selected_menu_items: Optional[List[int]] = None
    room_name: Optional[int] = None
    selected_arrangement: Optional[int] = None
    guest_name: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    guest_phone: Optional[str] = None
    deposit_amount: Optional[Decimal] = None


class EventBookingUpdate(BaseModel):
    arrival_date: Optional[date] = None
    arrival_time: Optional[time] = None
    event_type: Optional[str] = None
    event_theme: Optional[str] = None
    number_of_guests: Optional[int] = None
    event_duration: Optional[int] = None
    requires_catering: Optional[bool] = None
    requires_decoration: Optional[bool] = None
    requires_equipment: Optional[bool] = None
    equipment_needed: Optional[List[str]] = None
    special_requests: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[EventStatus] = None
    menu_item_ids: Optional[List[int]] = None


class MenuItemInBooking(BaseModel):
    id: int
    name: str
    price: Decimal
    category: str

    class Config:
        from_attributes = True


class EventBookingResponse(EventBookingBase):
    id: UUID
    company_id: UUID
    guest_id: Optional[UUID]
    guest_name: Optional[str]
    guest_email: Optional[str]
    guest_phone: Optional[str]
    status: EventStatus
    payment_status: PaymentStatus
    payment_url: Optional[str]
    total_amount: Decimal
    deposit_amount: Optional[Decimal]
    menu_items: List[MenuItemInBooking]
    created_at: datetime
    updated_at: datetime
