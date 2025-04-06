from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import UUID
from decimal import Decimal
from datetime import time, date, datetime
from sqlalchemy import ARRAY, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

import uuid
from sqlalchemy import JSON, DateTime
from sqlalchemy.sql import func
from app.database.database import Base
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import CHAR, JSONB
from sqlalchemy.orm import mapped_column, Mapped, relationship


from app.schemas.event_schema import EventStatus
from app.schemas.item_schema import ItemCategory
from app.schemas.order_schema import OrderStatusEnum, PaymentStatus
from app.schemas.reservation_schema import ReservationStatus
from app.schemas.room_schema import OutletType
from app.schemas.subscriptions import SubscriptionStatus, SubscriptionType
from app.schemas.user_schema import (
    CurencySymbol,
    PayType,
    PaymentGatwayEnum,
    PaymentTypeEnum,
    ReservationPaymentTypeEnum,
    UserType,
)


def user_unique_id():
    return str(uuid.uuid1()).replace("-", "")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid1, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    user_type: Mapped[UserType] = mapped_column(nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_subscribed: Mapped[bool] = mapped_column(default=False)
    notification_token: Mapped[str] = mapped_column(nullable=True)
    subscription_type: Mapped[SubscriptionType] = mapped_column(nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    # Company who created this staff (if applicable)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Relationships
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_resets = relationship(
        "PasswordReset", back_populates="user", cascade="all, delete-orphan"
    )
    user_profile = relationship("UserProfile", back_populates="user", uselist=False)
    company_profile = relationship(
        "CompanyProfile", back_populates="user", uselist=False
    )
    company = relationship("User", back_populates="staff", remote_side=[id])
    staff = relationship("User", back_populates="company")
    subscriptions = relationship("Subscription", back_populates="user")
    role = relationship("Role", back_populates="users", foreign_keys=[role_id])
    company_roles = relationship(
        "Role", back_populates="company", primaryjoin="User.id==Role.company_id"
    )

    qrcodes = relationship("QRCode", back_populates="user")
    departments = relationship("Department", back_populates="user")
    outlets = relationship("Outlet", back_populates="user")
    no_post_list = relationship("NoPost", back_populates="user")
    company_meeting_rooms: Mapped[list["MeetingRoom"]] = relationship(
        "MeetingRoom", back_populates="company"
    )
    seat_arrangements: Mapped[list["SeatArrangement"]] = relationship(
        "SeatArrangement", back_populates="company"
    )
    event_menu_items: Mapped[list["EventMenuItem"]] = relationship(
        "EventMenuItem", back_populates="company"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    guest_reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation", back_populates="guest", foreign_keys="[Reservation.guest_id]"
    )
    company_reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation", back_populates="company", foreign_keys="[Reservation.company_id]"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid1, nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    plan_name: Mapped[SubscriptionType] = mapped_column(default=SubscriptionType.TRIAL)
    amount: Mapped[Decimal] = mapped_column(default=0.00)
    # e.g., active, canceled
    status: Mapped[SubscriptionStatus] = mapped_column(
        default=SubscriptionStatus.ACTIVE
    )
    payment_link: Mapped[str] = mapped_column(nullable=True)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    end_date: Mapped[datetime] = mapped_column()

    user = relationship("User", back_populates="subscriptions")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid1, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column()
    phone_number: Mapped[str] = mapped_column(unique=True)
    department: Mapped[str] = mapped_column(nullable=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    rate_amount: Mapped[Decimal] = mapped_column(nullable=False)
    pay_type: Mapped[PayType] = mapped_column(default=PayType.MONTHLY)
    user = relationship("User", back_populates="user_profile")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid1, nullable=False, index=True
    )

    company_name: Mapped[str] = mapped_column(unique=True)
    address: Mapped[str] = mapped_column()
    phone_number: Mapped[str] = mapped_column(unique=True)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    logo_url: Mapped[str] = mapped_column(nullable=True)
    currency_symbol: Mapped[CurencySymbol] = mapped_column(
        nullable=True, default=CurencySymbol.NGN
    )
    user = relationship("User", back_populates="company_profile")

    api_key: Mapped[str] = mapped_column(unique=True)
    api_secret: Mapped[str] = mapped_column(unique=True)
    payment_gateway: Mapped[PaymentGatwayEnum] = mapped_column()


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, index=True, autoincrement=True
    )

    name: Mapped[str] = mapped_column(unique=False)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user_permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    company = relationship(
        "User", back_populates="company_roles", foreign_keys=[company_id]
    )
    users = relationship("User", back_populates="role", foreign_keys=[User.role_id])

    __table_args__ = (UniqueConstraint("name", "company_id", name="role_name"),)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, index=True, autoincrement=True
    )

    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column()


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, index=True, autoincrement=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(unique=False)
    user = relationship("User", back_populates="departments")
    __table_args__ = (UniqueConstraint("name", "company_id", name="department_name"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, index=True, autoincrement=True
    )
    company_id: Mapped[UUID]

    message: Mapped[str] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NoPost(Base):
    __tablename__ = "no_post_list"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, index=True, autoincrement=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    no_post_list: Mapped[str]
    user = relationship("User", back_populates="no_post_list")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class Outlet(Base):
    __tablename__ = "outlets"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, index=True)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str]
    user = relationship("User", back_populates="outlets")

    __table_args__ = (UniqueConstraint("name", "company_id", name="outlet_name"),)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class QRCode(Base):
    __tablename__ = "qrcodes"
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, index=True)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    room_or_table_numbers: Mapped[str]
    fill_color: Mapped[str] = mapped_column(nullable=True)
    back_color: Mapped[str] = mapped_column(nullable=True)
    outlet_type: Mapped[OutletType]
    user = relationship("User", back_populates="qrcodes")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, nullable=False, default=uuid.uuid1, index=True
    )
    token: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="refresh_tokens")


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid1, nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="password_resets")


class QRCodeLimit(Base):
    __tablename__ = "qrcode_limits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        default=SubscriptionType.TRIAL
    )
    max_qrcodes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class Payroll(Base):
    __tablename__ = "payrolls"

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    hours_or_days_worked: Mapped[int] = mapped_column(nullable=True)
    rate_amount: Mapped[Decimal] = mapped_column(nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(nullable=False)

    payment_status: Mapped[str] = mapped_column(nullable=False)
    payment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    overtime_rate: Mapped[Decimal] = mapped_column(nullable=False, default=0.0)
    night_shift_allowance: Mapped[Decimal] = mapped_column(nullable=False, default=0.0)

    days_worked: Mapped[int] = mapped_column(nullable=False, default=0)
    night_shifts: Mapped[int] = mapped_column(nullable=False, default=0)
    attendance_present: Mapped[int] = mapped_column(nullable=False, default=0)
    attendance_late: Mapped[int] = mapped_column(nullable=False, default=0)

    late_deduction: Mapped[Decimal] = mapped_column(nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Rate(Base):
    __tablename__ = "rates"

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str]
    pay_type: Mapped[PayType] = mapped_column(default=PayType.MONTHLY)
    rate_amount: Mapped[Decimal] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AttendanceQRCode(Base):
    __tablename__ = "attendance_qr_codes"

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    qrcode_image_url: Mapped[str] = mapped_column(nullable=True)
    fill_color: Mapped[str] = mapped_column(nullable=True)
    back_color: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"

    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(nullable=True)
    check_in: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    check_out: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NavItem(Base):
    __tablename__ = "nav_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path_name: Mapped[str] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(nullable=False)
    show: Mapped[bool] = mapped_column(nullable=False, default=True)


class ItemStock(Base):
    __tablename__ = "item_stocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    item: Mapped["Item"] = relationship("Item", back_populates="stocks")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(nullable=False)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    unit: Mapped[str] = mapped_column(nullable=False)  # e.g kg, piece
    reorder_point: Mapped[int] = mapped_column(default=0, nullable=False)
    category: Mapped[ItemCategory] = mapped_column(nullable=False)
    image_url: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    stocks: Mapped[list["ItemStock"]] = relationship(
        "ItemStock", back_populates="item", cascade="all, delete"
    )

    # Relationships
    order_items = relationship("OrderItem", back_populates="item")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid1, index=True)
    guest_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    outlet_id: Mapped[int] = mapped_column(nullable=True)
    company_id: Mapped[UUID]
    guest_name_or_email: Mapped[str]
    notes: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        nullable=False, default=OrderStatusEnum.NEW
    )
    total_amount: Mapped[Decimal] = mapped_column(nullable=False, default=0.0)
    room_or_table_number: Mapped[str]
    payment_url: Mapped[str] = mapped_column(nullable=True)
    payment_status: Mapped[str] = mapped_column(default="pending")
    payment_type: Mapped[str] = mapped_column(nullable=True)

    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    user = relationship("User", back_populates="orders", lazy="selectin")
    splits: Mapped[list["OrderSplit"]] = relationship(
        "OrderSplit",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        index=True,
        default=uuid.uuid1,
    )
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(nullable=False)

    order = relationship("Order", back_populates="order_items", lazy="selectin")
    item = relationship("Item", back_populates="order_items", lazy="selectin")


class OrderSplit(Base):
    __tablename__ = "order_splits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid1, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(nullable=False)
    # split_type can be either "amount" or "percent"
    split_type: Mapped[str] = mapped_column(nullable=False)
    # For "amount", value is the fixed monetary amount; for "percent", it is the percentage (e.g., 25 for 25%)
    value: Mapped[Decimal] = mapped_column(nullable=False)
    # Allocated is the computed amount for this split (after validating/splitting)
    allocated_amount: Mapped[Decimal] = mapped_column(
        nullable=False, default=Decimal("0.00")
    )
    payment_url: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    order = relationship("Order", back_populates="splits")


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid.uuid1)
    # Guest who made the reservation (can be null if company creates it)
    guest_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Company for which the reservation is made
    company_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # For company-created reservations where guest doesn't have an account
    guest_name: Mapped[str] = mapped_column(nullable=True)
    guest_email: Mapped[str] = mapped_column(nullable=True)
    guest_phone: Mapped[str] = mapped_column(nullable=True)

    arrival_date: Mapped[date]
    arrival_time: Mapped[time]
    number_of_guests: Mapped[int] = mapped_column(nullable=False)
    children: Mapped[int] = mapped_column(default=0, nullable=True)
    status: Mapped[ReservationStatus] = mapped_column(default=ReservationStatus.PENDING)
    notes: Mapped[str] = mapped_column(nullable=True)

    deposit_amount: Mapped[Decimal] = mapped_column(nullable=True, default=0.0)
    payment_status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING)
    payment_url: Mapped[str] = mapped_column(nullable=True)
    payment_type: Mapped[ReservationPaymentTypeEnum] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    guest = relationship(
        "User", back_populates="guest_reservations", foreign_keys=[guest_id]
    )
    company = relationship(
        "User", back_populates="company_reservations", foreign_keys=[company_id]
    )


class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"
    id: Mapped[int] = mapped_column(index=True, primary_key=True, autoincrement=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str]
    capacity: Mapped[int]
    amenities: Mapped[str]
    price: Mapped[Decimal]
    is_available: Mapped[bool] = mapped_column(default=True)

    bookings: Mapped[list["EventBooking"]] = relationship(
        "EventBooking", back_populates="meeting_room"
    )
    company = relationship("User", back_populates="company_meeting_rooms")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("name", "company_id", name="room_name"),)


class SeatArrangement(Base):
    __tablename__ = "seat_arrangements"
    id: Mapped[int] = mapped_column(index=True, primary_key=True, autoincrement=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str]
    image_url: Mapped[str]

    event_bookings: Mapped[list["EventBooking"]] = relationship(
        "EventBooking", back_populates="seat_arrangement"
    )
    company = relationship("User", back_populates="seat_arrangements")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("name", "company_id", name="arrangement_name"),)


class EventBooking(Base):
    __tablename__ = "event_bookings"
    id: Mapped[UUID] = mapped_column(primary_key=True, index=True, default=uuid.uuid1)
    # Guest who made the reservation (can be null if company creates it)
    guest_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Company for which the reservation is made
    company_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    meeting_room_id: Mapped[int] = mapped_column(
        ForeignKey("meeting_rooms.id"), nullable=True
    )
    seat_arrangement_id: Mapped[int] = mapped_column(
        ForeignKey("seat_arrangements.id"), nullable=True
    )
    name: Mapped[str]
    notes: Mapped[str] = mapped_column(nullable=True)
    special_requests: Mapped[str] = mapped_column(nullable=True)
    seating_arrangement: Mapped[str]
    location: Mapped[str]
    number_of_guest: Mapped[str]

    event_duration: Mapped[int] = mapped_column(nullable=False)  # duration in hours

    # Contact Person (if different from guest)
    contact_person_name: Mapped[str] = mapped_column(nullable=True)
    contact_person_phone: Mapped[str] = mapped_column(nullable=True)
    contact_person_email: Mapped[str] = mapped_column(nullable=True)

    # Additional Services
    requires_catering: Mapped[bool] = mapped_column(default=True)
    requires_decoration: Mapped[bool] = mapped_column(default=False)
    requires_equipment: Mapped[bool] = mapped_column(default=False)
    is_confirmed: Mapped[bool] = mapped_column(default=False)
    catering_size: Mapped[int] = mapped_column(nullable=True)

    # Equipment/Services Needed
    # projector, mic, etc.
    equipment_needed: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    # Financial
    total_amount: Mapped[Decimal] = mapped_column(
        nullable=False, default=Decimal("0.00")
    )
    deposit_amount: Mapped[Decimal] = mapped_column(nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING)
    payment_url: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[EventStatus] = mapped_column(default=EventStatus.PENDING)

    arrival_date: Mapped[date]
    arrival_time: Mapped[time]
    setup_time: Mapped[time] = mapped_column(nullable=True)
    end_time: Mapped[time] = mapped_column(nullable=True)

    meeting_room = relationship("MeetingRoom", back_populates="bookings")
    seat_arrangement = relationship("SeatArrangement", back_populates="event_bookings")
    menu_items: Mapped[list["EventMenuItem"]] = relationship(
        "EventMenuItem", secondary="event_booking_menu_items", back_populates="bookings"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventMenuItem(Base):
    __tablename__ = "event_menu_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(nullable=False)
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    image_url: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("name", "company_id", name="menu_name"),)

    # Relationship
    company = relationship("User", back_populates="event_menu_items")
    bookings: Mapped[list["EventBooking"]] = relationship(
        "EventBooking",
        secondary="event_booking_menu_items",
        back_populates="menu_items",
    )


class EventBookingMenuItem(Base):
    __tablename__ = "event_booking_menu_items"

    event_booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_bookings.id", ondelete="CASCADE"), primary_key=True
    )
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("event_menu_items.id", ondelete="CASCADE"), primary_key=True
    )
