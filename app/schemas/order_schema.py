from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class OrderStatusEnum(str, Enum):
    NEW = "New"
    IN_PROGRESS = "In progress"
    READY = "Ready"
    COMPLETED = "Completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDIND = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BillSplit(BaseModel):
    label: str
    split_type: Literal["amount", "percent"]
    value: Decimal


class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)

    class Config:
        from_attribute = True


class OrderCreate(BaseModel):
    company_id: UUID
    # outlet_id: int
    room_or_table_number: str
    items: list[OrderItemCreate]

    @field_validator("items")
    def validate_items(cls, items):
        if not items:
            raise ValueError("Order must contain at least one item")
        return items

    class Config:
        from_attribute = True


class OrderItemResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    price: Decimal
    name: str


class OrderResponse(BaseModel):
    id: UUID
    outlet_id: int
    guest_id: UUID
    status: str
    total_amount: Decimal
    room_or_table_number: str
    payment_url: str
    notes: str | None = None
    order_items: list[OrderItemResponse]
