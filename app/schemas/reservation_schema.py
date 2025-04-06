from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.order_schema import PaymentStatus


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ReservationBase(BaseModel):
    arrival_date: date
    arrival_time: time
    number_of_guests: int
    children: int | None
    notes: str | None = None
    deposit_amount: Decimal | None


class ReservationCreate(ReservationBase):
    company_id: UUID
    guest_name: str | None
    guest_email: EmailStr | None
    guest_phone: str | None


class ReservationUpdate(BaseModel):
    arrival_date: date = None
    arrival_time: time = None
    number_of_guests: int = None
    children: int = None
    notes: str = None
    status: ReservationStatus = None


class ReservationResponse(ReservationBase):
    id: UUID
    guest_id: UUID
    company_id: UUID
    guest_name: str
    guest_email: str
    guest_phone: str
    status: ReservationStatus
    payment_status: PaymentStatus
    payment_url: str
    created_at: datetime
    updated_at: datetime
