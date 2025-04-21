from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.auth import create_tokens, get_current_user, refresh_access_token
from app.database.database import get_db
from app.models.models import User
from app.schemas.user_schema import (
    PasswordResetConfirm,
    PasswordResetRequest,
    StaffUserCreate,
    TokenResponse,
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
    UserUpdatePassword,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", status_code=status.HTTP_200_OK)
async def login_user(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user = await auth_service.login_user(login_data=user_credentials, db=db)
        return await create_tokens(user_id=user.id, user_type=user.user_type, db=db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Logout user by revoking their refresh token"""
    try:
        success = await auth_service.logout_user(db=db, refresh_token=refresh_token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        return {"message": "Successfully logged out"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/register-guest", status_code=status.HTTP_201_CREATED)
async def register_guest(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserBase:
    try:
        return await auth_service.create_guest_user(user_data=user_data, db=db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register-company", status_code=status.HTTP_201_CREATED)
async def register_company(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserBase:
    try:
        return await auth_service.create_company_user(user_data=user_data, db=db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register-staff", status_code=status.HTTP_201_CREATED)
async def register_staff(
    user_data: StaffUserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserBase:
    try:
        return await auth_service.company_create_staff_user(
            user_data=user_data, db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/company-staff", status_code=status.HTTP_200_OK)
async def get_company_staff(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    try:
        return await auth_service.get_company_staff(
            db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/staff-details", status_code=status.HTTP_200_OK)
async def staff_details(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.get_staff_details(
            db=db, current_user=current_user, user_id=user_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/register-super-admin",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.create_super_admin_user(user_data=user_data, db=db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/register-admin-staff",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_admin_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.create_admin_user(
            user_data=user_data, db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update-user", status_code=status.HTTP_202_ACCEPTED)
async def update_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    try:
        return await auth_service.update_user(
            user_data=user_data, db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/update-password", status_code=status.HTTP_202_ACCEPTED)
async def update_password(
    user_data: UserUpdatePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    try:
        return await auth_service.update_password(
            user_data=user_data, db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
async def request_password_reset(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.request_password_reset(
            reset_request=data, db=db, background_tasks=background_tasks
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/confirm-password-reset", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.confirm_password_reset(reset_request=data, db=db)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Get new access token using refresh token from cookie"""
    try:
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )

        tokens = await refresh_access_token(refresh_token, db)

        return {
            "access_token": tokens.access_token,
            "token_type": "bearer"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
