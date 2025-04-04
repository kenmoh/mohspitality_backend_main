from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ANCELLED = "cancelled"
    COMPLETED = "completed"


class ReservationCreate(BaseModel):
    name: str
    date: datetime
    time: datetime
    adult: int
    deposit_amount: Decimal | None = None
    children: int | None = None
    notes: str | None = None


class ReservationResponse(ReservationCreate):
    id: str
    created_at: datetime
    updated_at: datetime
