import uuid
from fastapi import BackgroundTasks, HTTPException, status
from fastapi_mail import FastMail
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.config.config import settings
from app.models.models import PasswordReset, RefreshToken, User, UserProfile
from app.schemas.user_schema import (
    MessageSchema,
    PasswordResetConfirm,
    PasswordResetRequest,
    StaffUserCreate,
    UserCreate,
    UserLogin,
    UserResponse,
    UserType,
    UserUpdate,
    UserUpdatePassword,
)
from app.schemas.subscriptions import (
    SubscriptionStatus,
    SubscriptionType,

)
from app.services.profile_service import (
    check_permission,
    get_role_by_name,
    setup_company_roles,
)
from app.services.subscription_service import create_staff_subscription, create_subscription
from app.utils.utils import get_company_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def create_super_admin_user(
    db: AsyncSession, user_data: UserCreate
) -> UserResponse:
    """
    Create a new admin user in the database.

    Args:
        db: Database session
        user_data: User data from request

    Returns:
        The newly created user
    """
    # Check if email already exists
    email_exists = await db.execute(select(User).where(User.email == user_data.email))
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # Create the user
    user = User(
        email=user_data.email,
        password=hash_password(user_data.password),  # Hash password
        user_type=UserType.COMPANY,
        is_active=True,
        is_superuser=True,
        subscription_type=None,
        updated_at=datetime.now(),
    )

    # Add user to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def create_admin_user(
    db: AsyncSession, user_data: UserCreate, current_user: User
) -> UserResponse:
    """
    Create a new admin user in the database.

    Args:
        db: Database session
        user_data: User data from request

    Returns:
        The newly created user
    """
    # Check if email already exists
    email_exists = await db.execute(select(User).where(User.email == user_data.email))
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # Create the user
    user = User(
        email=user_data.email,
        password=hash_password(user_data.password),  # Hash password
        user_type=UserType.SALES,
        company_id=current_user.id,
        is_active=True,
        is_superuser=False,
        subscription_type=None,
        updated_at=datetime.now(),
    )

    # Add user to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def create_guest_user(db: AsyncSession, user_data: UserCreate) -> UserResponse:
    """
    Create a new user in the database.

    Args:
        db: Database session
        user_data: User data from request

    Returns:
        The newly created user
    """
    # Check if email already exists
    email_exists = await db.execute(select(User).where(User.email == user_data.email))
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # Create the user
    user = User(
        email=user_data.email,
        password=hash_password(user_data.password),  # Hash password
        user_type=UserType.GUEST,
        is_active=True,
        is_superuser=False,
        subscription_type=None,
        updated_at=datetime.now(),
    )

    # Add user to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def create_company_user(db: AsyncSession, user_data: UserCreate) -> UserResponse:
    """
    Create a new user in the database.

    Args:
        db: Database session
        user_data: User data from request

    Returns:
        The newly created user
    """
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    email_exists = await db.execute(stmt)
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    # Create the user
    user = User(
        email=user_data.email,
        password=hash_password(user_data.password), 
        user_type=UserType.COMPANY,
        is_active=True,
        is_superuser=False,
        updated_at=datetime.now(),
    )

    # Add user to database
    db.add(user)
    await db.commit()
    await db.refresh(user)
 
    # await setup_company_roles(db=db, company_id=user.id)
    await create_subscription(db=db, plan_name=SubscriptionType.TRIAL, user_id=user.id)
    
    return user


async def company_create_staff_user(
    db: AsyncSession, user_data: StaffUserCreate, current_user: User
) -> UserResponse:
    """Create a staff user with profile in a single transaction"""
    if current_user.user_type != UserType.COMPANY:
        raise HTTPException(status_code=403, detail="Company admins only")
    check_permission(user=current_user, required_permission="create_users")
    
    # Check if email exists
    stmt = select(User).where(User.email == user_data.email)
    email_exists = await db.execute(stmt)
    if email_exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    try:
        # Create the staff user
        new_staff = User(
            email=user_data.email,
            password=hash_password(user_data.password),
            user_type=UserType.STAFF,
            company_id=current_user.id,
            role_id=user_data.role_id,
            subscription_type=current_user.subscription_type,
            updated_at=datetime.now(),
        )
        db.add(new_staff)
        await db.flush()  # Get the ID without committing
        
        # Get company role
        """
        role = await get_role_by_name(
		role_name=user_data.role_name,
		db=db,
		current_user=current_user
	)
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role '{user_data.role_name}' not found in your company"
            )
        """
        # Create user profile
        user_profile = UserProfile(
            full_name=user_data.full_name,
            phone_number=user_data.phone_number,
            department_id=user_data.department,
            user_id=new_staff.id,
            pay_type=user_data.pay_type
        )
        db.add(user_profile)
        await db.commit()
        
        # Set role
        # new_staff.role_id = role.id
        
        await create_staff_subscription(
            db=db, staff_user=new_staff, current_user=current_user
        )
        
              
        await db.refresh(new_staff)
        return new_staff
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def login_user(db: AsyncSession, login_data: UserLogin) -> User:
    """
    Args:
            db: Database session
            login_data: Login credentials

    Returns:
            Authenticated user or None if authentication fails
    """
    # Find user by username
    stmt = select(User).where(User.email == login_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Verify password
    if not verify_password(login_data.password, user.password):
        return None

    # Check if user is active
    if not user.is_active:
        return None

    return user


async def update_user(
    db: AsyncSession, user_data: UserUpdate, current_user: User
) -> User:
    """
    Args:
            db: Database session
            user_id: ID of the user to update
            user_data: Updated user data

    Returns:
            Updated user
    """
    # Get the user
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update values that are provided
    if user_data.email is not None:
        # Check if email is already taken by another user
        stmt = select(User).where(
            User.email == user_data.email, User.id != current_user.id
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user.email = user_data.email

    # Save changes
    await db.commit()
    await db.refresh(user)

    return user


async def update_password(
    db: AsyncSession, current_user: User, password_data: UserUpdatePassword
) -> User:
    """
    Args:
            db: Database session
            user_id: ID of the user to update
            password_data: Current and new password

    Returns:
            Updated user
    """
    # Get the user
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Hash and set new password
    user.password = hash_password(password_data.new_password)

    # Revoke all refresh tokens for this user
    await db.execute(
        (RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id, RefreshToken.is_revoked == False
        )
        .values(is_revoked=True)
    )

    # Save changes
    await db.commit()
    await db.refresh(user)

    return user


async def send_password_reset_email(
    email: EmailStr, reset_token: str, background_tasks: BackgroundTasks
):
    """
    Send a password reset email to the user.
    Args:
            email: Email address of the user
            reset_token: Password reset token
            background_tasks: FastAPI background tasks
    """
    # Create reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    # Create email message
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"""
		<html>
		<body>
		    <p>We received a request to reset your password. If you didn't make this request, please ignore this email.</p>
		    <p>To reset your password, click the link below:</p>
		    <p><a href="{reset_link}">Reset Password</a></p>
		    <p>This link will expire in {settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hours.</p>
		</body>
		</html>
		""",
        subtype="html",
    )

    # Send email in background
    fastmail = FastMail(message)
    background_tasks.add_task(fastmail.send_message, message)


async def request_password_reset(
    db: AsyncSession,
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
) -> bool:
    """
    Request a password reset for a user.
    Args:
            db: Database session
            reset_request: Password reset request data
            background_tasks: FastAPI background tasks

    Returns:
            True if password reset was requested successfully
    """
    # Find user by email
    stmt = select(User).where(User.email == reset_request.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Always return true, even if user not found, to prevent email enumeration
    if not user:
        return True

    # Generate reset token
    reset_token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(
        hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
    )

    # Create password reset record
    password_reset = PasswordReset(
        token=reset_token, user_id=user.id, expires_at=expires_at
    )

    # Add password reset to database
    db.add(password_reset)
    await db.commit()

    # Send password reset email
    await send_password_reset_email(user.email, reset_token, background_tasks)

    return True


async def confirm_password_reset(
    db: AsyncSession, reset_confirm: PasswordResetConfirm
) -> User:
    """
    Confirm a password reset and change the user's password.
    Args:
            db: Database session
            reset_confirm: Password reset confirmation data

    Returns:
            User with updated password
    """
    # Find password reset record
    stmt = select(PasswordReset).where(
        PasswordReset.token == reset_confirm.token,
        PasswordReset.expires_at > datetime.now(),
        PasswordReset.is_used == False,
    )
    result = await db.execute(stmt)
    password_reset = result.scalar_one_or_none()

    if not password_reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # Get the user
    stmt = select(User).where(User.id == password_reset.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Mark token as used
    password_reset.is_used = True

    # Hash and set new password
    user.password = hash_password(reset_confirm.new_password)

    # Revoke all refresh tokens for this user
    await db.execute(
        (RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.is_revoked == False)
        .values(is_revoked=True)
    )

    # Save changes
    await db.commit()

    return user


async def get_staff_details(db: AsyncSession, current_user: User, user_id: uuid.UUID) -> UserResponse:
    """Get staff details including profile, department and role information"""
    company_id = get_company_id(current_user)
    stmt = (
        select(User)
        .options(
            joinedload(User.user_profile).joinedload(UserProfile.department),
            joinedload(User.role)
        )
        .where(User.id == user_id)
        .where(User.company_id == company_id)
    )
    result = await db.execute(stmt)
    user = result.unique().scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "id": str(user.id),
        "email": user.email,
        "company_id": str(user.company_id) if user.company_id else None,
        "role_name": user.role.name if user.role else None,
        "full_name": user.user_profile.full_name if user.user_profile else None,
        "phone_number": user.user_profile.phone_number if user.user_profile else None,
        "department": user.user_profile.department.name if user.user_profile and user.user_profile.department else None,
        "pay_type": user.user_profile.pay_type if user.user_profile else None,
        "created_at": user.created_at
    }

async def get_company_staff(db: AsyncSession, current_user: User) -> list[UserResponse]:
    """Get company staff including profile, department and role information"""
    company_id = get_company_id(current_user)
    stmt = (
        select(User)
        .options(
            joinedload(User.user_profile).joinedload(UserProfile.department),
            joinedload(User.role)
        )
        .where(User.company_id == company_id)
    )
    result = await db.execute(stmt)
    users = result.unique().scalars().all()
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "company_id": str(user.company_id) if user.company_id else None,
            "role_name": user.role.name if user.role else None,
            "full_name": user.user_profile.full_name if user.user_profile else None,
            "phone_number": user.user_profile.phone_number if user.user_profile else None,
            "department": user.user_profile.department.name if user.user_profile and user.user_profile.department else None,
            "payment_type": user.user_profile.pay_type if user.user_profile else None,
            "created_at": user.created_at,
        } for user in users]


async def logout_user(db: AsyncSession, refresh_token: str) -> bool:
    """
    Logout user by revoking their refresh token
    Args:
        db: Database session
        refresh_token: The refresh token to revoke
    Returns:
        True if token was revoked successfully
    """
    stmt = (
        select(RefreshToken)
        .where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False
        )
    )
    result = await db.execute(stmt)
    token = result.scalar_one_or_none()

    if not token:
        return False

    # Revoke the token
    token.is_revoked = True
    await db.commit()

    return True
