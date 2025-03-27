from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class OrderItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(gt=0)

    class Config:
        from_attribute = True


class OrderCreate(BaseModel):
    company_id: UUID
    outlet_id: int
    guest_id: str
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
    id: int
    outlet_id: int
    guest_id: UUID
    status: str
    total: Decimal
    room_or_table_number: str
    payment_url: str | None = None
    order_items: list[OrderItemResponse]
