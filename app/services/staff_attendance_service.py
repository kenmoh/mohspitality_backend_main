from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import StaffAttendance
from app.schemas.staff_attendance_schema import (
    StaffAttendanceCreate,
    StaffAttendanceUpdate,
)
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError


async def create_staff_attendance(
    db: AsyncSession, staff_attendance: StaffAttendanceCreate
) -> StaffAttendance:
    try:
        db_staff_attendance = StaffAttendance(**staff_attendance.model_dump())
        db.add(db_staff_attendance)
        await db.commit()
        await db.refresh(db_staff_attendance)
        return db_staff_attendance
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def get_staff_attendance(
    db: AsyncSession, staff_attendance_id: int
) -> StaffAttendance | None:
    try:
        result = await db.execute(
            select(StaffAttendance).filter(StaffAttendance.id == staff_attendance_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def update_staff_attendance(
    db: AsyncSession,
    staff_attendance_id: int,
    staff_attendance_update: StaffAttendanceUpdate,
) -> StaffAttendance | None:
    try:
        result = await db.execute(
            select(StaffAttendance).filter(StaffAttendance.id == staff_attendance_id)
        )
        db_staff_attendance = result.scalar_one_or_none()
        if db_staff_attendance:
            for key, value in staff_attendance_update.dict(exclude_unset=True).items():
                setattr(db_staff_attendance, key, value)
            await db.commit()
            await db.refresh(db_staff_attendance)
            return db_staff_attendance
        return None
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def delete_staff_attendance(db: AsyncSession, staff_attendance_id: int) -> bool:
    try:
        result = await db.execute(
            select(StaffAttendance).filter(StaffAttendance.id == staff_attendance_id)
        )
        db_staff_attendance = result.scalar_one_or_none()
        if db_staff_attendance:
            await db.delete(db_staff_attendance)
            await db.commit()
            return True
        return False
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def get_all_staff_attendance(
    db: AsyncSession, company_id: UUID, skip: int = 0, limit: int = 100
):
    try:
        result = await db.execute(
            select(StaffAttendance)
            .filter(StaffAttendance.company_id == company_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def get_staff_attendance_by_date_range(
    db: AsyncSession, company_id: UUID, start_date: datetime, end_date: datetime
):
    try:
        result = await db.execute(
            select(StaffAttendance).filter(
                StaffAttendance.company_id == company_id,
                StaffAttendance.check_in >= start_date,
                StaffAttendance.check_out <= end_date,
            )
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
