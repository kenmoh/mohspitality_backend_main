import logging
import os
import asyncio
from fastapi import Depends, status, APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.order_schema import PaymentStatus
from rave_python import Rave

from app.auth import get_current_user

from app.models.models import (
    EventBooking,
    Order,

)
from app.database.database import get_db


from app.config.config import settings

from app.utils.utils import unique_id, verify_transaction_tx_ref


class MessageResponseSchema(BaseModel):
    message: str


payment_router = APIRouter(prefix="/api/payment", tags=["Payment"])
# payment.token = settings.PAYMENT_TOKEN
rave = Rave(
    settings.FLW_PUBLIC_KEY,
    settings.FLW_SECRET_KEY,
    # os.getenv('FLW_ENCRYPTION_KEY'),
    production=True,
    usingEnv=False,
)

templates = Jinja2Templates(directory="templates")


# CONFIRM ORDER PAYMENT
@payment_router.get(
    "/callback",
    status_code=status.HTTP_200_OK,
    response_description="Payment Callback",
)
async def payment_callback(request: Request, db: Session = Depends(get_db)):
    tx_ref = request.query_params["tx_ref"]
    tx_status = request.query_params["status"]

    order_query = (
        select(Order)
        .where(unique_id(Order.id) == tx_ref)
    )
    result = await db.execute(order_query)
    order = result.scalar_one_or_none()

    event_query = (
        select(EventBooking)
        .where(unique_id(EventBooking.id) == tx_ref)
    )
    result = await db.execute(event_query)
    event = result.scalar_one_or_none()

    if (
        tx_status == "successful"
        and verify_transaction_tx_ref(tx_ref).get("data").get("status") == "successful"
    ):
        order.payment_status = PaymentStatus.PAID
        db.commit()
        return {"payment_status": order.payment_status}

    if tx_status == "cancelled":
        order.payment_status = PaymentStatus.CANCELLED
        db.commit()
        return {"payment_status": order.payment_status}

    else:
        order.payment_status = PaymentStatus.FAILED
        db.commit()
        return {"payment_status": order.payment_status}


# SUCCESS WEBHOOK
# @payment_router.post(
#     "/webhook",
#     status_code=status.HTTP_200_OK,
#     response_description="Success | Failure Webhook",
#     response_model=MessageResponseSchema,
# )
# async def process_webhook(
#     request: Request,
#     background_task: BackgroundTasks,
#     db: Session = Depends(get_db),
# ):

#     signature = request.headers.get("verif-hash")

#     if signature is None or (signature != settings.FLW_SECRET_HASH):
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     payload = await request.json()
#     db_order = db.query(Order).filter(Order.id == payload["txRef"]).first()
#     db_tranx = db.query(Transaction).filter(
#         Transaction.id == payload["txRef"]).first()

#     order = db_order or db_tranx
#     try:
#         if (
#             payload["status"] == "successful"
#             and payload["charged_amount"] == order.total_cost
#             and payload["amount"] == order.total_cost
#             and payload["currency"] == "NGN"
#             and verify_transaction_tx_ref(payload["txRef"]).get("data").get("status")
#             == "successful"
#             and order.payment_status != PaymentStatus.PAID
#         ):

#             return {"message": "Success"}
#     except Exception as e:
#         logging.error(f"Error processing webhook: {e}")
#         raise HTTPException(status_code=500, detail="INTERNAL_SERVER_ERROR")
#     return {"message": "Failed"}
