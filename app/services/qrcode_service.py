from datetime import datetime
from pathlib import Path
import zipfile
from fastapi import HTTPException, status
import qrcode
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import QRCode, QRCodeLimit, User
from app.schemas.room_schema import OutletType, QRCodeCreate, QRCodeResponse
from app.schemas.subscriptions import SubscriptionType
from app.schemas.user_schema import UserType


async def initialize_qr_code_limits(db: AsyncSession):
    """
    Initialize QR code limits for different subscription types.
    This function should be run during application startup or as part of a migration.
    """
    print("Initializing QR code limits...")

    # Define the limits for each subscription type
    limits = [
        {"subscription_type": SubscriptionType.TRIAL, "max_qrcodes": 5},
        {"subscription_type": SubscriptionType.BASIC, "max_qrcodes": 5},
        {"subscription_type": SubscriptionType.PREMIUM, "max_qrcodes": 50},
        {"subscription_type": SubscriptionType.ENTERPRISE, "max_qrcodes": 500},
    ]

    # Check existing records
    for limit_data in limits:
        subscription_type = limit_data["subscription_type"]

        # Check if record already exists
        result = await db.execute(
            select(QRCodeLimit).where(
                QRCodeLimit.subscription_type == subscription_type
            )
        )
        existing_limit = result.scalar_one_or_none()

        if existing_limit:
            # Update existing record if needed
            existing_limit.max_qrcodes = limit_data["max_qrcodes"]
            existing_limit.updated_at = datetime.now()
            print(
                f"Updated limit for {subscription_type.name}: {limit_data['max_qrcodes']}"
            )
        else:
            # Create new record
            new_limit = QRCodeLimit(
                subscription_type=subscription_type,
                max_qrcodes=limit_data["max_qrcodes"],
                updated_at=datetime.now(),
            )
            db.add(new_limit)
            print(
                f"Created limit for {subscription_type.name}: {limit_data['max_qrcodes']}"
            )

    # Commit changes
    await db.commit()
    print("QR code limits initialization completed.")


# ================== QR CODE ================


async def create_qrcode(
    db: AsyncSession, current_user: User, qrcode_data: QRCodeCreate
) -> str:
    base_url: str = "https://mohspitality.com"
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )

    rooms_list = [room.strip() for room in qrcode_data.room_or_table_numbers.split(",")]
    rooms_set = set(rooms_list)
    unique_rooms = list(rooms_set)

    unique_rooms_string = ", ".join(sorted(rooms_set))

    # Get user's subscription type
    subscription_type = current_user.subscription_type

    # Check limit for this subscription type
    limit_record = await db.execute(
        select(QRCodeLimit).where(QRCodeLimit.subscription_type == subscription_type)
    )
    limit = limit_record.scalar_one_or_none()

    max_qrcodes = limit.max_qrcodes

    # Count existing QR codes for this company
    count_query = select(func.count(QRCode.id)).where(QRCode.company_id == company_id)
    result = await db.execute(count_query)
    current_count = result.scalar_one()

    # Check if limit reached
    if current_count >= max_qrcodes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your plan has reached the maximum QR code generation limit of {max_qrcodes}. Please upgrade.",
        )

    # Generate QR codes
    try:
        # Create temporary zip file
        temp_dir = Path("room-qrcodes")
        temp_dir.mkdir(exist_ok=True)

        zip_path = temp_dir / f"qrcodes-{company_id}.zip"

        with zipfile.ZipFile(zip_path, "w") as zip_file:
            for room in unique_rooms:
                if qrcode_data.outlet_type == OutletType.ROOM_SERVICE:
                    room_table_url = f"""{base_url}/users/{company_id}?room={room}"""
                elif qrcode_data.outlet_type == OutletType.RESTAURANT:
                    room_table_url = f"""{base_url}/users/{company_id}?table={room}"""

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(room_table_url)
                qr.make(fit=True)

                qr_image = qr.make_image(
                    fill_color=qrcode_data.fill_color or "black",
                    back_color=qrcode_data.back_color or "white",
                )

                # Save QR code to temporary file
                temp_file = temp_dir / f"room_{room}.png"
                qr_image.save(temp_file)

                # Add to zip file
                zip_file.write(temp_file, f"room_{room}.png")

                # Clean up temporary file
                temp_file.unlink()

            qr_code = QRCode(
                company_id=company_id,
                room_or_table_numbers=unique_rooms_string,
                fill_color=qrcode_data.fill_color,
                back_color=qrcode_data.back_color,
                outlet_type=qrcode_data.outlet_type,
            )
            db.add(qr_code)
            await db.commit()
            await db.refresh(qr_code)
            return str(zip_path)

    except Exception as e:
        # Clean up any remaining temporary files
        for file in temp_dir.glob("*"):
            file.unlink()
        raise Exception(f"Failed to generate QR codes: {str(e)}")


async def get_qrcode(db: AsyncSession, current_user: User) -> list[QRCodeResponse]:
    company_id = (
        current_user.id
        if current_user.user_type == UserType.COMPANY
        else current_user.company_id
    )
    stmt = select(QRCode).where(QRCode.company_id == company_id)
    result = await db.execute(stmt)
    qr_codes = result.all()

    return qr_codes
