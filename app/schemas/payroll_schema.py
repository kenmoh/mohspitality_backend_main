from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PayrollSchema(BaseModel):
    user_id: UUID
    company_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    hours_or_days_worked: int | None = None
    rate_amount: Decimal
    total_amount: Decimal
    payment_status: str
    payment_date: datetime | None = None
    overtime_rate: Decimal = 0.0
    night_shift_allowance: Decimal = 0.0
    days_worked: int = 0
    night_shifts: int = 0
    attendance_present: int = 0
    attendance_late: int = 0
    late_deduction: Decimal = 0.0

    class Config:
        orm_mode = True


class PayrollResponseSchema(PayrollSchema):
    id: int
    created_at: datetime
    updated_at: datetime
