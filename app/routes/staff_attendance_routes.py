from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID
from datetime import datetime

from app.database.database import get_db
from app.services.staff_attendance_service import (
    create_staff_attendance,
    get_staff_attendance,
    update_staff_attendance,
    delete_staff_attendance,
    get_all_staff_attendance,
    get_staff_attendance_by_date_range
)
from app.schemas.staff_attendance_schema import (
    StaffAttendanceCreate,
    StaffAttendanceUpdate,
    StaffAttendanceResponse
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/staff_attendance", tags=["Staff Attendance"])


@router.post("", response_model=StaffAttendanceResponse)
async def create_staff_attendance_route(staff_attendance: StaffAttendanceCreate, db: AsyncSession = Depends(get_db)):
    return await create_staff_attendance(db=db, staff_attendance=staff_attendance)


@router.get("/{staff_attendance_id}", response_model=StaffAttendanceResponse)
async def get_staff_attendance_route(staff_attendance_id: int, db: AsyncSession = Depends(get_db)):
    db_staff_attendance = await get_staff_attendance(
        db=db, staff_attendance_id=staff_attendance_id)
    if db_staff_attendance is None:
        raise HTTPException(
            status_code=404, detail="Staff Attendance not found")
    return db_staff_attendance


@router.put("/{staff_attendance_id}", response_model=StaffAttendanceResponse)
async def update_staff_attendance_route(staff_attendance_id: int, staff_attendance_update: StaffAttendanceUpdate, db: AsyncSession = Depends(get_db)):
    db_staff_attendance = await update_staff_attendance(
        db=db, staff_attendance_id=staff_attendance_id, staff_attendance_update=staff_attendance_update)
    if db_staff_attendance is None:
        raise HTTPException(
            status_code=404, detail="Staff Attendance not found")
    return db_staff_attendance


@router.delete("/{staff_attendance_id}")
async def delete_staff_attendance_route(staff_attendance_id: int, db: AsyncSession = Depends(get_db)):
    if await delete_staff_attendance(db=db, staff_attendance_id=staff_attendance_id):
        return {"message": "Staff Attendance deleted successfully"}
    else:
        raise HTTPException(
            status_code=404, detail="Staff Attendance not found")


@router.get("/", response_model=List[StaffAttendanceResponse])
async def get_all_staff_attendance_route(company_id: UUID, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    return await get_all_staff_attendance(db=db, company_id=company_id, skip=skip, limit=limit)


@router.get("/by_date_range/", response_model=List[StaffAttendanceResponse])
async def get_staff_attendance_by_date_range_route(company_id: UUID, start_date: datetime, end_date: datetime, db: AsyncSession = Depends(get_db)):
    return await get_staff_attendance_by_date_range(db=db, company_id=company_id, start_date=start_date, end_date=end_date)
