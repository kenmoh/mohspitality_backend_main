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
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UpdateOrderStatus(BaseModel):
    status: OrderStatusEnum


class OrderItemSplit(BaseModel):
    item_id: int
    quantity: int


class OrderSplitRequest(BaseModel):
    items: list[OrderItemSplit]


class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)
    name: str


class OrderCreate(BaseModel):
    company_id: UUID
    # outlet_id: int
    notes: str | None = None
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
    # id: UUID
    item_id: int
    quantity: int
    price: Decimal
    name: str


class OrderResponse(BaseModel):
    id: UUID
    # outlet_id: int
    guest_id: UUID
    original_order_id: UUID
    status: str
    total_amount: Decimal
    room_or_table_number: str
    payment_url: str
    notes: str | None = None
    is_split: bool
    order_items: list[OrderItemResponse]


class OrderItemSummary(BaseModel):
    item_id: int
    name: str
    quantity: int
    price: Decimal
    total: Decimal


class OrderSummaryResponse(BaseModel):
    order_id: UUID
    total_amount: Decimal
    items: list[OrderItemSummary]


class SplitDetailResponse(BaseModel):
    label: str
    split_type: str
    requested_value: str
    allocated: Decimal
    payment_url: str


class BillSplitResponse(BaseModel):
    order_id: UUID
    original_amount: Decimal
    remaining_amount: Decimal
    total_split_amount: Decimal
    splits: list[SplitDetailResponse]

    # order_id: UUID
    # total_amount: Decimal
    # splits: list[SplitDetailResponse]
    # remainder: Decimal
