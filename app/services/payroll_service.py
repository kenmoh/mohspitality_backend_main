from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Payroll
from app.schemas.payroll_schema import PayrollSchema


class PayrollService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payroll(self, payroll: PayrollSchema) -> Payroll:
        db_payroll = Payroll(**payroll.model_dump())
        self.db.add(db_payroll)
        await self.db.commit()
        await self.db.refresh(db_payroll)
        return db_payroll

    async def get_payroll(self, payroll_id: int) -> Payroll | None:
        result = await self.db.execute(select(Payroll).where(Payroll.id == payroll_id))
        return result.scalar_one_or_none()

    async def get_payrolls_by_user(self, user_id: UUID) -> list[Payroll]:
        result = await self.db.execute(
            select(Payroll).where(Payroll.user_id == user_id)
        )
        return result.scalars().all()

    async def update_payroll(
        self, payroll_id: int, payroll: PayrollSchema
    ) -> Payroll | None:
        db_payroll = await self.get_payroll(payroll_id)
        if db_payroll:
            for key, value in payroll.dict(exclude_unset=True).items():
                setattr(db_payroll, key, value)
            await self.db.commit()
            await self.db.refresh(db_payroll)
            return db_payroll
        return None

    async def delete_payroll(self, payroll_id: int) -> bool:
        db_payroll = await self.get_payroll(payroll_id)
        if db_payroll:
            await self.db.delete(db_payroll)
            await self.db.commit()
            return True
        return False
