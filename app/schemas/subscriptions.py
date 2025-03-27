from datetime import date
from enum import Enum
from uuid import UUID
from pydantic import BaseModel


class SubscriptionType(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"


class CreateSubscription(BaseModel):
    plan_name: SubscriptionType
    start_date: date
    end_date: date


class Updateubscription(BaseModel):
    plan_name: SubscriptionType


class SubscriptionResponse(BaseModel):
    id: int
    user_id: UUID
    plan_name: SubscriptionType
    status: SubscriptionStatus
    start_date: date
    end_date: date
