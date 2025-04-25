from enum import Enum
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
import re


class CurencySymbol(str, Enum):
    NGN = "NGN"
    GHS = "GHS"
    KES = "KES"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    CAD = "CAD"
    AUS = "AUS"


class RotaStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PayType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ShiftType(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    NIGHT = "night"
    SWING = "swing"
    LEAVE = "leave"


class EventReservationEnum(str, Enum):
    UPCOMING = ("upcoming",)
    ONGOING = ("ongoing",)
    COMPLETED = ("completed",)
    CANCELLED = "cancelled"


class AttendanceStatusEnum(str, Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"


class UserType(str, Enum):
    COMPANY = "company"
    GUEST = "guest"
    STAFF = "staff"
    SALES = "sales"
    DEVELOPERS = "developers"
    SUPER_ADMIN = "super-admin"


class ResourceEnum(str, Enum):
    USERS = "users"
    ORDERS = "orders"
    ITEMS = "items"
    STOCK = "stocks"
    PAYMENTS = "payments"
    LAUNDRY = "laundry"
    STORE = "store"
    PERMISSIONS = "permissions"
    DEPARTMENTS = "departments"
    OUTLETS = "outlets"
    RATE = "rate"


class ActionEnum(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class PaymentGatwayEnum(str, Enum):
    FLUTTERWAVE = "flutterwave"
    PAYSTACK = "paystack"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class PaymentTypeEnum(str, Enum):
    CARD = "card"
    CHARGE_TO_ROOM = "charge_to_room"
    CASH = "cash"


class ReservationPaymentTypeEnum(str, Enum):
    CARD = "card"
    CASH = "cash"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, data: str):
        # Check if password meets requirements
        if not re.search(r"[A-Z]", data):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", data):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", data):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', data):
            raise ValueError("Password must contain at least one special character")
        return data


class StaffUserCreate(UserCreate):
    full_name: str
    phone_number: str
    department: int
    role_id: int
    pay_type: PayType


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None


class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    # @field_validator("password", mode="before")
    # @classmethod
    # def validate_password(cls, data: str):
    #     # Check if password meets requirements
    #     if not re.search(r"[A-Z]", data):
    #         raise ValueError("Password must contain at least one uppercase letter")
    #     if not re.search(r"[a-z]", data):
    #         raise ValueError("Password must contain at least one lowercase letter")
    #     if not re.search(r"\d", data):
    #         raise ValueError("Password must contain at least one digit")
    #     if not re.search(r'[!@#$%^&*(),.?":{}|<>]', data):
    #         raise ValueError("Password must contain at least one special character")
    #     return data


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    # @field_validator("password", mode="before")
    # @classmethod
    # def validate_password(cls, data: str):
    #     # Check if password meets requirements
    #     if not re.search(r"[A-Z]", data):
    #         raise ValueError(
    #             "Password must contain at least one uppercase letter")
    #     if not re.search(r"[a-z]", data):
    #         raise ValueError(
    #             "Password must contain at least one lowercase letter")
    #     if not re.search(r"\d", data):
    #         raise ValueError("Password must contain at least one digit")
    #     if not re.search(r'[!@#$%^&*(),.?":{}|<>]', data):
    #         raise ValueError(
    #             "Password must contain at least one special character")
    #     return data


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_type: str
    allowed_routes: list[str] = []


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    company_id: UUID | None = None
    role_name: str | None = None
    full_name: str | None = None
    phone_number: str | None = None
    department: str | None = None
    payment_type: str | None = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class MessageSchema(BaseModel):
    subject: str
    recipients: list[EmailStr]
    body: str
    subtype: str = Field(default="html")


class StaffRoleCreate(BaseModel):
    name: str
    permissions: list[int] = []


class NavItemResponse(BaseModel):
    id: int
    path_name: str
    path: str

    class Config:
        from_attributes = True


class DepartmentResponse(BaseModel):
    id: int
    company_id: UUID
    name: str
    nav_items: list[NavItemResponse]

    class Config:
        from_attributes = True


class OutletCreate(BaseModel):
    name: str


class OutleResponse(OutletCreate):
    id: str


class DepartmentCreate(BaseModel):
    name: str
    nav_items: list[int] = []


class Permission(BaseModel):
    name: str


class NoPostCreate(BaseModel):
    name: str


class NoPostResponse(NoPostCreate):
    company_id: UUID


class PermissionResponse(Permission):
    id: int
    name: str
    description: str


class RolePermissionResponse(PermissionResponse):
    pass


class AddPermissionsToRole(BaseModel):
    permissions: list[str]


class RoleCreateResponse(BaseModel):
    id: int
    company_id: UUID
    name: str
    permissions: list[PermissionResponse | None] = []


class AssignRoleToStaff(BaseModel):
    name: str


class UserProfileResponse(BaseModel):
    full_name: str
    user_type: str
    phone_number: str
    user_id: UUID
    department: DepartmentResponse

    class Config:
        from_attributes = True


"""
{
  "full_name": "Kenneth",
  "phone_number": "090990099889",
  "user_id": "090990099889",
  "department": {
    "id": 15,
    "name": "kitchen",
    "nav_items": [
      {
        "id": 1,
        "path_name": "staff",
        "path": "/staff"
      }
    ]
  }
}

"""
