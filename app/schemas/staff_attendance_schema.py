from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class StaffAttendanceCreate(BaseModel):
    company_id: UUID
    full_name: str
    check_in: datetime
    check_out: datetime


class StaffAttendanceUpdate(BaseModel):
    full_name: str | None = None
    check_in: datetime | None = None
    check_out: datetime | None = None


class StaffAttendanceResponse(BaseModel):
    id: int
    company_id: UUID
    full_name: str
    check_in: datetime
    check_out: datetime

    class Config:
        orm_mode = True
