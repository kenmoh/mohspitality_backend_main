import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import requests
from app.config.config import settings
from app.models.models import CompanyProfile, Subscription, User, Order

flutterwave_base_url = "https://api.flutterwave.com/v3"
mohospitality_base_url = "http://localhost:8000"
f = Fernet(settings.ENCRYPTION_KEY)


def unique_id(id: uuid.UUID) -> str:
    return str(id).replace("-", "")


def encrypt_data(data: str) -> str:
    return f.encrypt(data.encode()).decode()


def decrypt_data(data: str) -> str:
    return f.decrypt(data.encode()).decode()


async def get_company_api_secret(_company_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(CompanyProfile.api_secret)
        .where(CompanyProfile.company_id == _company_id)
    )
    api_secret = result.scalars().first()
    return decrypt_data(api_secret)


def get_subscription_payment_link(subscription: Subscription, current_user: User):
    headers = {"Authorization": f"Bearer {settings.FLW_SECRET_KEY}"}
    details = {
        "tx_ref": subscription.id,
        "amount": str(subscription.amount),
        "currency": "USD",
        "redirect_url": f"{mohospitality_base_url}/payment/subscription-payment-callback",
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


async def get_order_payment_link(order: Order, db: AsyncSession, current_user: User):
    headers = {
        "Authorization": f"Bearer {await get_company_api_secret(order.company_id, db=db)}"}
    details = {
        "tx_ref": unique_id(order.id),
        "amount": str(order.total_amount),
        "currency": "NGN",
        "redirect_url": f"{mohospitality_base_url}/payment/subscription-payment-callback",
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
