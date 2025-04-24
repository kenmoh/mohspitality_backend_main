
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas.profile_schema import (
    CreateCompanyProfile,
    CreateCompanyProfileResponse,
    CreateStaffUserProfile,
    CreateUserProfileBase,
    MessageResponse,
    UpdateCompanyPaymentGateway,
    UpdateCompanyProfile,
)
from app.schemas.room_schema import (
    NoPostCreate,
    NoPostResponse,
    RatetCreate,
    RatetResponse,
)
from app.schemas.user_schema import (
    AddPermissionsToRole,
    AssignRoleToStaff,
    DepartmentCreate,
    DepartmentResponse,
    PermissionResponse,
    RoleCreateResponse,
    StaffRoleCreate,
    UserProfileResponse,
    UserResponse,
    NavItemResponse
)
from app.services import profile_service

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/compnay-profile", status_code=status.HTTP_201_CREATED)
async def create_company_profile(
    data: CreateCompanyProfile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateCompanyProfileResponse:
    try:
        return await profile_service.create_company_profile(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/guest-profile", status_code=status.HTTP_201_CREATED)
async def create_guest_profile(
    data: CreateUserProfileBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateUserProfileBase:
    try:
        return await profile_service.create_guest_profile(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/staff-profile", status_code=status.HTTP_201_CREATED)
async def create_staff_profile(
    data: CreateStaffUserProfile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    try:
        return await profile_service.create_staff_profile(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse | CreateCompanyProfileResponse:
    try:
        return await profile_service.get_user_profile(
            db=db,  current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/staff-role", status_code=status.HTTP_201_CREATED)
async def create_staff_role(
    data: StaffRoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleCreateResponse:
    try:
        return await profile_service.create_staff_role(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/all-company-roles")
async def get_all_company_staff_roles(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[RoleCreateResponse]:
    try:
        return await profile_service.get_all_company_staff_roles(
            db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("")
async def get_all_users(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    result = await db.execute(select(User))
    return result.scalars().all()


@router.get("/{role_id}/company-role")
async def role_details(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleCreateResponse:
    try:
        return await profile_service.get_company_staff_role(
            role_id=role_id, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{role_id}/company-role", status_code=status.HTTP_202_ACCEPTED)
async def update_role_permission(
    role_id: int,
    data: AddPermissionsToRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleCreateResponse:
    try:
        return await profile_service.update_role_with_permissions(
            role_id=role_id, data=data, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/assign-role-to-staff", status_code=status.HTTP_202_ACCEPTED)
async def assign_role_to_staff(
    user_id: str,
    data: AssignRoleToStaff,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleCreateResponse:
    try:
        return await profile_service.assign_role_to_user(
            user_id=user_id, data=data, db=db, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/all-permissions")
async def get_all_permissions(
    db: AsyncSession = Depends(get_db),
) -> list[PermissionResponse]:
    try:
        return await profile_service.get_all_permissions(db=db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/company-profile-update", status_code=status.HTTP_202_ACCEPTED)
async def update_company_profile(
    data: UpdateCompanyProfile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateCompanyProfileResponse:
    try:
        return await profile_service.update_company_profile(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/company-payment-gateway-update", status_code=status.HTTP_202_ACCEPTED)
async def update_company_payment_gateway(
    data: UpdateCompanyPaymentGateway,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    try:
        return await profile_service.update_company_payment_gateway(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ============== DEPARTMENT =================


@router.post("/company-create-department", status_code=status.HTTP_201_CREATED)
async def create_company_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    try:
        return await profile_service.create_department(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/{department_id}/company-delete-department", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_company_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await profile_service.delete_company_department(
            db=db, current_user=current_user, department_id=department_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/company-departments", status_code=status.HTTP_200_OK)
async def get_company_department(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DepartmentResponse]:
    try:
        return await profile_service.get_company_departments(
            db=db,
            current_user=current_user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/nav-items", status_code=status.HTTP_200_OK)
async def get_nav_items(
    db: AsyncSession = Depends(get_db),
) -> list[NavItemResponse]:
    try:
        return await profile_service.get_nav_items(
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============== No POST =================


@router.post("/company-create-no-post-list", status_code=status.HTTP_201_CREATED)
async def create_company_no_post_list(
    data: NoPostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoPostResponse:
    try:
        return await profile_service.create_no_post_list(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/company-no-post-list", status_code=status.HTTP_200_OK)
async def get_company_no_post_listt(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DepartmentResponse]:
    try:
        return await profile_service.get_company_no_post_list(
            db=db,
            current_user=current_user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============== OUTLET =================
@router.post("/company-create-outlet", status_code=status.HTTP_201_CREATED)
async def create_company_outlet(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DepartmentResponse:
    try:
        return await profile_service.create_outlet(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete(
    "/{outlet_id}/company-delete-outlet", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_company_outlet(
    outlet_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await profile_service.delete_company_outlet(
            db=db, current_user=current_user, outlet_id=outlet_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/company-outlets", status_code=status.HTTP_200_OK)
async def get_company_outlets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DepartmentResponse]:
    try:
        return await profile_service.get_company_outlets(
            db=db,
            current_user=current_user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============== RATE =================
@router.post("/company-rates", status_code=status.HTTP_201_CREATED)
async def create_company_rate(
    data: RatetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RatetResponse:
    try:
        return await profile_service.create_rate(
            db=db, data=data, current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/company-rates", status_code=status.HTTP_201_CREATED)
async def get_company_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RatetResponse]:
    try:
        return await profile_service.get_company_rates(db=db, current_user=current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{rate_id}/company-delete-rate", status_code=status.HTTP_204_NO_CONTENT)
async def create_company_rate(
    rate_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        return await profile_service.delete_company_rate(
            db=db, current_user=current_user, rate_id=rate_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
