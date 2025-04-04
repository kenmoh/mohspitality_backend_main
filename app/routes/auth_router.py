from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession


from app.auth.auth import create_tokens, get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.user_schema import (
    PasswordResetConfirm,
    PasswordResetRequest,
    StaffUserCreate,
    TokenResponse,
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
        return await create_tokens(user_id=user.id, db=db)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register-guest", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    try:
        return await auth_service.create_guest_user(user_data=user_data, db=db)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register-company", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    try:
        return await auth_service.create_company_user(user_data=user_data, db=db)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/register-staff", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: StaffUserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.company_create_staff_user(
            user_data=user_data, db=db, current_user=current_user
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/confirm-password-reset", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    try:
        return await auth_service.confirm_password_reset(reset_request=data, db=db)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
