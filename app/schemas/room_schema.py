from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from pydantic import BaseModel

from app.schemas.user_schema import PayType


class OutletType(str, Enum):
    RESTAURANT = "restaurant"
    ROOM_SERVICE = "room_service"


class NoPostCreate(BaseModel):
    no_post_list: str


class RatetCreate(BaseModel):
    name: str
    pay_type: PayType
    rate_amount: Decimal


class RatetResponse(RatetCreate):
    id: int
    company_id: UUID


class NoPostResponse(NoPostCreate):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class OutletCreate(BaseModel):
    name: str


class OutletResponse(OutletCreate):
    id: int
    company_id: UUID
    created_at: datetime


class QRCodeCreate(BaseModel):
    room_or_table_numbers: str
    fill_color: str | None = None
    back_color: str | None = None
    outlet_type: OutletType


class QRCodeResponse(QRCodeCreate):
    id: int
    company_id: UUID
    created_at: datetime
    updated_at: datetime
