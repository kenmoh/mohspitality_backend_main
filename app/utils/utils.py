from decimal import Decimal
import uuid
import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import requests
from app.config.config import settings
from app.models.models import CompanyProfile, Subscription, User
from app.schemas.user_schema import UserType

flutterwave_base_url = "https://api.flutterwave.com/v3"
mohspitality_base_url = "http://localhost:8000"
f = Fernet(settings.ENCRYPTION_KEY)


def unique_id(id: uuid.UUID) -> str:
    return str(id).replace("-", "")


def encrypt_data(data: str) -> str:
    return f.encrypt(data.encode()).decode()


def decrypt_data(data: str) -> str:
    return f.decrypt(data.encode()).decode()


async def get_company_api_secret(_company_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(CompanyProfile.api_secret).where(
            CompanyProfile.company_id == _company_id
        )
    )
    api_secret = result.scalars().first()

    return decrypt_data(api_secret)


def get_subscription_payment_link(subscription: Subscription, current_user: User):
    headers = {"Authorization": f"Bearer {settings.FLW_SECRET_KEY}"}
    details = {
        "tx_ref": subscription.id,
        "amount": str(subscription.amount),
        "currency": "USD",
        "redirect_url": f"{mohspitality_base_url}/payment/subscription-payment-callback",
        "payment_options": "card, banktransfer, internetbanking, opay, account",
        "bank_transfer_options": {"expires": 3600},
        "customer": {
            "email": current_user.email,
            "username": (current_user.company_profile.company_name),
        },
    }

    response = requests.post(
        f"{flutterwave_base_url}/payments", json=details, headers=headers
    )
    response_data = response.json()
    link = response_data["data"]["link"]

    return link


async def get_order_payment_link(
    db: AsyncSession,
    company_id: uuid.UUID,
    current_user: User,
    _id: uuid.UUID,
    amount: Decimal,
):
    try:
        headers = {
            "Authorization": f"Bearer {await get_company_api_secret(company_id, db=db)}"
        }
        details = {
            "tx_ref": unique_id(_id),
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": f"{mohspitality_base_url}/payment/subscription-payment-callback",
            "payment_options": "card, banktransfer, internetbanking, opay, account",
            "bank_transfer_options": {"expires": 3600},
            "customer": {
                "email": current_user.email,
                # "username": (current_user.company_profile.company_name),
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{flutterwave_base_url}/payments", json=details, headers=headers
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data["data"]["link"]

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Payment gateway error: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate payment link: {str(e)}"
        )


def check_current_user_id(current_user: User):
    user_id = (
        current_user.id
        if current_user.user_type == (UserType.COMPANY or UserType.GUEST)
        else current_user.company_id
    )

    return user_id
