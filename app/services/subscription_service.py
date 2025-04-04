from datetime import datetime
from select import select
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Subscription, User
from app.schemas.subscriptions import (
    CreateSubscription,
    SubscriptionStatus,
    SubscriptionResponse,
    SubscriptionType,
    Updateubscription,
)
from app.config.config import settings
from app.schemas.user_schema import UserType
from app.utils.utils import get_subscription_payment_link

TRIAL_DURATION = 14
TRIAL_AMOUNT = 0.00
PLAN_DURATION = 30
BASICT_AMOUNT = 399.99
PREMIUM_AMOUNT = 899.99
ENTERPRISE_AMOUNT = 1199.99


async def create_subscription(
    db: AsyncSession, data: CreateSubscription, current_user: User
) -> SubscriptionResponse:
    try:
        # Determine the duration based on the plan type
        if data.plan_name == SubscriptionType.TRIAL:
            duration = TRIAL_DURATION  # Trial lasts for 14 days
            amount = TRIAL_AMOUNT
        elif data.plan_name == SubscriptionType.BASIC:
            duration = PLAN_DURATION  # Other plans last for 30 days
            amount = BASICT_AMOUNT
        elif data.plan_name == SubscriptionType.PREMIUM:
            duration = PLAN_DURATION
            amount = PREMIUM_AMOUNT
        elif data.plan_name == SubscriptionType.ENTERPRISE:
            duration = PLAN_DURATION
            amount = ENTERPRISE_AMOUNT
        # Create Subscription
        subscription = Subscription(
            user_id=current_user.id,
            plan_name=data.plan_name,
            end_date=datetime.today() + datetime.timedelta(days=duration),
            amount=amount,
        )

        # Add subscription to database
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        subscription.payment_link = get_subscription_payment_link(
            subscription=subscription, current_user=current_user
        )

        return subscription
    except Exception as e:
        raise e


async def create_staff_subscription(
    db: AsyncSession, staff_user: User, current_user: User
) -> SubscriptionResponse:
    # Check if the company has an active subscription
    company_subscription = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.plan_name == current_user.subscriptions.plan_name,
        )
    )
    company_subscription = company_subscription.scalar_one_or_none()

    if not company_subscription:
        raise Exception("The company does not have an active subscription.")

    # Create a new subscription for the staff user
    staff_subscription = Subscription(
        user_id=staff_user.id,
        plan_name=company_subscription.plan_name,  # Inherit the plan name
        start_date=company_subscription.start_date,
        end_date=company_subscription.end_date,
        status=SubscriptionStatus.ACTIVE,
    )

    # Add subscription to database
    db.add(staff_subscription)
    await db.commit()
    await db.refresh(staff_subscription)

    return staff_subscription


async def update_company_subscription(
    db: AsyncSession, data: Updateubscription, current_user: User
) -> SubscriptionResponse:
    # Get the company profile
    stmt = select(Subscription).where(
        Subscription.user_id == current_user.id, User.user_type == UserType.COMPANY
    )
    result = await db.execute(stmt)
    company_subscription = result.scalar_one_or_none()

    if not company_subscription:
        raise Exception("No subscription exists for this company")

    # Update the company subscription details
    company_subscription.plan_name = data.plan_name

    # Save changes
    await db.commit()
    await db.refresh(company_subscription)

    company_subscription.payment_link = get_subscription_payment_link(
        company_subscription
    )

    # Update all staff subscriptions
    await update_staff_subscriptions(db=db, current_user=current_user)

    return company_subscription


async def update_staff_subscriptions(db: AsyncSession, current_user: User):
    # Get all staff users associated with the company
    staff_users = await db.execute(
        select(User).where(User.company_id == current_user.company_id)
    )
    staff_users = staff_users.scalars().all()

    for staff_user in staff_users:
        # Update each staff user's subscription based on the company subscription
        staff_subscription = await db.execute(
            select(Subscription).where(Subscription.user_id == staff_user.id)
        )
        staff_subscription = staff_subscription.scalar_one_or_none()

        if staff_subscription:
            staff_subscription.plan_name = current_user.subscriptions.plan_name
            # Update other fields as necessary
            await db.commit()
            await db.refresh(staff_subscription)


async def check_and_update_expired_subscriptions(db: AsyncSession):
    # Get all subscriptions that have expired
    expired_subscriptions = await db.execute(
        select(Subscription).where(Subscription.end_date < datetime.now())
    )
    expired_subscriptions = expired_subscriptions.scalars().all()

    for subscription in expired_subscriptions:
        # Update the subscription status to expired
        subscription.status = SubscriptionStatus.EXPIRED
        await db.commit()
        await db.refresh(subscription)

        await update_staff_subscriptions(db, expired_subscriptions.user.company_id)


async def check_and_update_expired_subscriptions(db: AsyncSession):
    # Get all subscriptions that have expired
    expired_subscriptions = await db.execute(
        select(Subscription).where(Subscription.end_date < datetime.utcnow())
    )
    expired_subscriptions = expired_subscriptions.scalars().all()

    for subscription in expired_subscriptions:
        # Update the subscription status to expired
        subscription.status = "expired"
        await db.commit()
        await db.refresh(subscription)

        # Optionally, update all staff subscriptions linked to this company subscription
        await update_staff_subscriptions(db, subscription)


def create_flutterwave_subscription(plan: Subscription, current_user):
    url = "https://api.flutterwave.com/v3/subscriptions"
    headers = {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "tx_ref": plan.id,
        "amount": str(plan.amount),
        "name": plan.plan_name,  # Name of the subscription
        "customer": current_user.company_profile.company_name,
        "currency": "USD",
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def create_flutterwave_customer(email, name):
    url = "https://api.flutterwave.com/v3/charges?type=subscription"
    headers = {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "email": email,
        "name": name,
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


def update_flutterwave_subscription(subscription_id, new_plan_id):
    url = f"https://api.flutterwave.com/v3/subscriptions/{subscription_id}"
    headers = {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "plan": new_plan_id  # The new plan ID
    }
    response = requests.put(url, json=data, headers=headers)
    return response.json()


async def notify_user(email, subject, body):
    # Implement email sending logic here
    pass


async def notify_trial_expiration(user_email, trial_end_date):
    subject = "Your Trial is Ending Soon"
    body = f"Dear User,\n\nYour trial will expire on {trial_end_date}. Please consider upgrading your subscription.\n\nBest Regards,\nMOHospitality"
    await notify_user(user_email, subject, body)


async def check_and_notify_users(db: AsyncSession):
    # Get users whose trial is expiring in the next 3 days
    upcoming_expirations = await db.execute(
        select(Subscription).where(
            Subscription.end_date <= datetime.utcnow() + datetime.timedelta(days=3)
        )
    )
    users = upcoming_expirations.scalars().all()

    for user in users:
        await notify_trial_expiration(user.email, user.end_date)
