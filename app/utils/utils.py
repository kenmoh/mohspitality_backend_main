from fastapi import HTTPException, status
from cryptography.fernet import Fernet
import requests
from app.config.config import settings
from app.models.models import Subscription, User

flutterwave_base_url = "https://api.flutterwave.com/v3"
mohospitality_base_url = "http://localhost:8000"
f = Fernet(settings.ENCRYPTION_KEY)


def encrypt_data(data: str) -> str:
    return f.encrypt(data.encode()).decode()


def decrypt_data(data: str) -> str:
    return f.decrypt(data.encode()).decode()


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


# action_resource_list = [
#     f"{action.value}_{resource.value}"
#     for action in ActionEnum
#     for resource in ResourceEnum
# ]
