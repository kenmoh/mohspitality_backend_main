from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel


class ItemCategory(str, Enum):
    FOOD = "food"
    BEVERAGE = "beverage"
    LINEN = "linen"


class CreateItemSchema(BaseModel):
    name: str
    description: str
    unit: str
    reorder_point: int
    price: Decimal
    image_url: str
    category: ItemCategory


class ItemStockSchema(BaseModel):
    quantity: int
    notes: str | None = None


class ItemStockReturnSchema(ItemStockSchema):
    id: int
    created_at: datetime


class CreateItemReturnSchema(CreateItemSchema):
    id: int
    quantity: int
    stocks: list[ItemStockReturnSchema]
