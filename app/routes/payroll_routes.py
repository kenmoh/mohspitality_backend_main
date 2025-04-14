from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.schemas.payroll_schema import PayrollSchema, PayrollResponseSchema
from app.services.payroll_service import PayrollService

router = APIRouter(tags=['Payrolls'], prefix="/api/payrolls")


@router.post("", response_model=PayrollResponseSchema, status_code=201)
async def create_payroll(payroll: PayrollSchema, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Create a new payroll.
    """
    payroll_service = PayrollService(db)
    return await payroll_service.create_payroll(payroll)


@router.get("/{payroll_id}", response_model=PayrollResponseSchema)
async def get_payroll(payroll_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Get a payroll by its ID.
    """
    payroll_service = PayrollService(db)
    payroll = await payroll_service.get_payroll(payroll_id)
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    return payroll


@router.get("/user/{user_id}", response_model=list[PayrollResponseSchema])
async def get_payrolls_by_user(user_id: UUID, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Get all payrolls for a specific user.
    """
    payroll_service = PayrollService(db)
    payrolls = await payroll_service.get_payrolls_by_user(user_id)
    return payrolls


@router.put("/{payroll_id}", response_model=PayrollResponseSchema)
async def update_payroll(payroll_id: int, payroll: PayrollSchema, db: AsyncSession = Depends(get_db)) -> Any:
    """
    Update a payroll.
    """
    payroll_service = PayrollService(db)
    updated_payroll = await payroll_service.update_payroll(payroll_id, payroll)
    if not updated_payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    return updated_payroll


@router.delete("/{payroll_id}", status_code=204)
async def delete_payroll(payroll_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a payroll.
    """
    payroll_service = PayrollService(db)
    if not await payroll_service.delete_payroll(payroll_id):
        raise HTTPException(status_code=404, detail="Payroll not found")
    return None
