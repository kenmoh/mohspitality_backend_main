from datetime import datetime
import re
from uuid import UUID
from fastapi import HTTPException, status
from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.models import (
    Department,
    NoPost,
    Outlet,
    Permission,
    Role,
    UserProfile,
    CompanyProfile,
    User,
    Rate,
    NavItem,
)

from app.schemas.profile_schema import (
    CreateCompanyProfile,
    CreateStaffUserProfile,
    CreateUserProfileBase,
    CreateCompanyProfileResponse,
    MessageResponse,
    UpdateCompanyPaymentGateway,
    UpdateCompanyProfile,
)
from app.schemas.room_schema import (
    NoPostCreate,
    NoPostResponse,
    OutletCreate,
    RatetCreate,
    RatetResponse,
)
from app.schemas.user_schema import (
    ActionEnum,
    AddPermissionsToRole,
    DepartmentCreate,
    DepartmentResponse,
    OutleResponse,
    PermissionResponse,
    ResourceEnum,
    RoleCreateResponse,
    RolePermissionResponse,
    StaffRoleCreate,
    UserProfileResponse,
    UserType,
    NavItemResponse,
)
from app.utils.utils import encrypt_data, get_company_id


# def generate_permission(action: ActionEnum, resource: ResourceEnum) -> str:
#     return f"{action.value}_{resource.value}"


# async def get_permission_by_name(name: str, db: AsyncSession):
#     result = await db.execute(select(Permission).where(Permission.name == name))
#     permission = result.scalar_one_or_none()
#     permission_dict = {
#         "id": permission.id,
#         "name": permission.name,
#         "description": permission.description,
#     }
#     return permission_dict


# async def setup_company_roles(db: AsyncSession, company_id: str, user: User) -> Role:
#     """
#     Set up default roles and permissions for a newly created company,
#     and assign the admin role to the registering user.

#     Args:
#         db: Database session
#         company_id: The company ID
#         user: The user to assign the admin role to

#     Returns:
#         The created admin role
#     """
#     # Generate all possible permissions
#     action_resource_list = [
#         f"{action.value}_{resource.value}"
#         for action in ActionEnum
#         for resource in ResourceEnum
#     ]

#     try:
#         # Check if we're already in a transaction
#         if db.in_transaction():
#             # If already in transaction, just proceed without begin()
#             company_role = Role(
#                 name="company-admin",
#                 company_id=company_id,
#                 user_permissions=action_resource_list,

#             )
#             db.add(company_role)
#             await db.flush()

#             user_role = UserRole(
#                 user_id=user.id,
#                 role_id=company_role.id,
#                 assigned_by_company_id=company_id,

#             )

#             db.add(user_role)
#             await db.flush()

#             user.role_id = company_role.id

#             await db.commit()
#             await db.refresh(company_role)
#         else:
#             # If no transaction exists, create one
#             async with db.begin():
#                 company_role = Role(
#                     name="company-admin",
#                     company_id=company_id,
#                     user_permissions=action_resource_list,
#                 )
#                 db.add(company_role)
#                 await db.flush()

#                 user_role = UserRole(
#                     user_id=user.id,
#                     role_id=company_role.id,
#                     assigned_by_company_id=company_id,

#                 )

#                 db.add(user_role)
#                 await db.flush()
#                 user.role_id = company_role.id

#             await db.commit()
#             await db.refresh(company_role)

#         return company_role

#     except IntegrityError as e:
#         await db.rollback()
#         if "role_name" in str(e.orig):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Default roles already exist for this company"
#             )
#         raise HTTPException(
#             status_code=500,
#             detail="Failed to create company roles"
#         )
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected error: {str(e)}"
#         )

# # async def setup_company_roles(db: AsyncSession, company_id: str, user: User):
# #     """
# #     Set up default roles and permissions for a newly created company.

# #     Args:
# #         db: Database session
# #         company_user: The company user for which to create roles

# #     Returns:
# List of created roles
# #     """

# #     action_resource_list = [
# #         f"{action.value}_{resource.value}"
# #         for action in ActionEnum
# #         for resource in ResourceEnum
# #     ]

# #     # Create the role
# #     company_role = Role(
# #         company_id=company_id,
# #         name="company-admin",
# #         user_permissions=action_resource_list,
# #     )

# #     db.add(company_role)
# #     await db.commit()
# #     await db.refresh(company_role)

# #     return company_role


# async def pre_create_permissions(db: AsyncSession):
#     # Fetch existing permissions from the database
#     result = await db.execute(select(Permission.name))
#     existing_permissions = set(result.scalars().all())

#     permissions = []
#     for action in ActionEnum:
#         for resource in ResourceEnum:
#             permission_name = generate_permission(action, resource)
#             if (
#                 permission_name not in existing_permissions
#             ):  # Check if permission already exists
#                 permissions.append(
#                     {
#                         "name": permission_name,
#                         "description": f"{action.value} {resource.value}",
#                     }
#                 )

#     # Add new permissions to the database
#     if permissions:
#         for perm in permissions:
#             db.add(Permission(**perm))
#         await db.commit()
#         print(f"Added {len(permissions)} new permissions to the database.")
#     else:
#         print("No new permissions to add.")


# def has_permission(user: User, required_permission: str) -> bool:
#     """
#     Check permissions without additional database queries by using loaded relationships
#     """
#     # Superusers bypass all permission checks
#     if user.is_superuser:
#         return True

#     # Check primary role permissions (if loaded)
#     if user.role and user.role.user_permissions:
#         if required_permission in user.role.user_permissions:
#             return True

#     # Check permissions from all assigned roles (if relationship is loaded)
#     if hasattr(user, 'user_role_assignments'):
#         for assignment in user.user_role_assignments:
#             if (assignment.role and
#                 assignment.role.user_permissions and
#                     required_permission in assignment.role.user_permissions):
#                 return True

#     return False


# async def check_permission(user: User, required_permission: str):
#     """
#     Fast permission check that relies on pre-loaded relationships
#     """
#     if not has_permission(user, required_permission):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail=f"Permission denied. Required: {required_permission}",
#             headers={"WWW-Authenticate": "Bearer"}
#         )

# # def has_permission(user: User, required_permission: str) -> bool:
# #     # Fetch the user's role and permissions
# #     if not user.role or not user.role.user_permissions:
# #         return False

# #     # Check if the required_permission matches any permission name in the list
# #     return any(
# #         perm.get("name") == required_permission for perm in user.role.user_permissions
# #     )


# # async def check_permission(user: User, required_permission: str):
# #     if not has_permission(user, required_permission):
# #         raise HTTPException(
# #             status_code=status.HTTP_403_FORBIDDEN,
# #             detail=f"Permission denied: {required_permission}",
# #         )


# async def get_role_by_name(
#     role_name: str, db: AsyncSession, current_user: User | None = None
# ):
#     if current_user:
#         stmt = select(Role).where(
#             (Role.name == role_name) & (Role.company_id == current_user.id)
#         )
#         role = await db.execute(stmt)
#         return role.scalar_one_or_none()
#     else:
#         stmt = select(Role).where(Role.name == role_name)
#         role = await db.execute(stmt)
#         return role.scalar_one_or_none()


def generate_permission(action: ActionEnum, resource: ResourceEnum) -> str:
    return f"{action.value}_{resource.value}"


async def get_permission_by_name(name: str, db: AsyncSession):
    result = await db.execute(select(Permission).where(Permission.name == name))
    permission = result.scalar_one_or_none()
    permission_dict = {
        "id": permission.id,
        "name": permission.name,
        "description": permission.description,
    }
    return permission_dict


async def setup_company_roles(db: AsyncSession, company_id: UUID, name: str):
    """
    Set up default roles and permissions for a newly created company.
    Ensures no duplicate permissions are added.

    Args:
        db: Database session
        company_user: The company user for which to create roles
        name: Name of the role to create

    Returns:
        List of created roles
    """
    result = await db.execute(select(Permission).distinct())
    permissions = result.scalars().all()

    # Create the role
    company_role = Role(
        company_id=company_id,
        name=name,
        permissions=permissions,
    )

    db.add(company_role)
    await db.commit()
    await db.refresh(company_role)

    return company_role


async def pre_create_permissions(db: AsyncSession):
    # Fetch existing permissions from the database
    result = await db.execute(select(Permission.name))
    existing_permissions = set(result.scalars().all())

    permissions = []
    for action in ActionEnum:
        for resource in ResourceEnum:
            permission_name = generate_permission(action, resource)
            if (
                permission_name not in existing_permissions
            ):  # Check if permission already exists
                permissions.append(
                    {
                        "name": permission_name,
                        "description": f"{action.value} {resource.value}",
                    }
                )

    # Add new permissions to the database
    if permissions:
        for perm in permissions:
            db.add(Permission(**perm))
        await db.commit()
        print(f"Added {len(permissions)} new permissions to the database.")
    else:
        print("No new permissions to add.")
        
        
async def get_user_allowed_routes(user: User, db: AsyncSession) -> list[str]:
    # Ensure user has a profile and department loaded
    stmt = (
        select(User)
        .options(
            selectinload(User.user_profile)
            .selectinload(UserProfile.department)
            .selectinload(Department.nav_items)
        )
        .where(User.id == user.id)
    )

    result = await db.execute(stmt)
    user_with_navs = result.scalar_one_or_none()

    if not user_with_navs or not user_with_navs.user_profile:
        return []

    department = user_with_navs.user_profile.department
    if not department:
        return []

    # Extract all nav item paths
    return [nav_item.path for nav_item in department.nav_items]

def has_permission(user: User, required_permission: str) -> bool:
    """
    Check if a user has the specified permission through their role.

    Args:
        user: The User object to check
        required_permission: The permission name to check for

    Returns:
        bool: True if user has the permission, False otherwise
    """
    # Check if user has a role and the role has loaded permissions
    if not user.role or not user.role.permissions:
        return False

    # Check if any permission's name matches the required permission
    return any(
        permission.name == required_permission for permission in user.role.permissions
    )


async def check_permission(user: User, required_permission: str):
    if not has_permission(user, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {required_permission}",
        )


async def get_role_by_name(
    role_name: str, db: AsyncSession, current_user: User | None = None
):
    if current_user:
        stmt = select(Role).where(
            (Role.name == role_name) & (Role.company_id == current_user.id)
        )
        role = await db.execute(stmt)
        return role.scalar_one_or_none()
    else:
        stmt = select(Role).where(Role.name == role_name)
        role = await db.execute(stmt)
        return role.scalar_one_or_none()


async def create_company_profile(
    db: AsyncSession, data: CreateCompanyProfile, current_user: User
) -> CreateCompanyProfileResponse:
    try:
        # Create Profile
        company_profile = CompanyProfile(
            company_name=data.company_name,
            phone_number=data.phone_number,
            address=data.address,
            api_key=encrypt_data(data.api_key),
            api_secret=encrypt_data(data.api_secret),
            payment_gateway=data.payment_gateway,
            company_id=current_user.id,
        )

        # Add profile to database
        db.add(company_profile)
        await db.commit()
        await db.refresh(company_profile)

        return company_profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def create_guest_profile(
    db: AsyncSession, data: CreateUserProfileBase, current_user: User
) -> CreateUserProfileBase:
    try:
        # Create Profile
        guest_profile = UserProfile(
            full_name=data.full_name,
            phone_number=data.phone_number,
            user_id=current_user.id,
        )

        # Add profile to database
        db.add(guest_profile)
        await db.commit()
        await db.refresh(guest_profile)

        return guest_profile
    except Exception as e:
        raise e


async def create_staff_profile(
    db: AsyncSession, data: CreateStaffUserProfile, current_user: User
) -> UserProfileResponse:
    try:
        # Ensure department exists
        stmt = select(Department).where(Department.id == data.department_id)
        result = await db.execute(stmt)
        department = result.scalar_one_or_none()
        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )

        # Create Profile
        staff_profile = UserProfile(
            full_name=data.full_name,
            phone_number=data.phone_number,
            department_id=data.department_id,
            user_id=current_user.id,
        )

        db.add(staff_profile)
        await db.commit()
        await db.refresh(staff_profile, ["department"])

        # Optionally, return a response model with department relation loaded
        return staff_profile
    except Exception as e:
        raise e


async def get_user_profile(
    current_user: User, db: AsyncSession
) -> UserProfileResponse | CreateCompanyProfileResponse:
    if current_user.user_type == UserType.STAFF:
        stmt = (
            select(UserProfile)
            .where(UserProfile.user_id == current_user.id)
            .options(
                joinedload(UserProfile.department).joinedload(Department.nav_items)
            )
        )
        result = await db.execute(stmt)
        profile = result.unique().scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        department = profile.department
        department_data = None
        if department:
            department_data = {
                "id": department.id,
                "name": department.name,
                "company_id": department.company_id,
                "nav_items": [
                    {
                        "id": nav_item.id,
                        "path_name": nav_item.path_name,
                        "path": nav_item.path,
                    }
                    for nav_item in department.nav_items
                ],
            }

        profile_dict = {
            "full_name": profile.full_name,
            "user_type": current_user.user_type,
            "phone_number": profile.phone_number,
            "user_id": str(profile.user_id),
            "department": department_data,
        }

        return UserProfileResponse.model_validate(profile_dict)
    elif current_user.user_type == UserType.COMPANY:
        stmt = (
            select(User)
            .where(User.user_id == current_user.id)
            .options(joinedload(User.company_profile).joinedload(User.profile_image))
        )
        result = await db.execute(stmt)
        profile = result.unique().scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        profile_dict = {
            "company_id": profile.id,
            "company_name": profile.company_profile.company_name,
            "phone_number": profile.company_profile.phone_number,
            "address": profile.company_profile.address,
            "image_url": profile.profile_image.image_url,
        }

        return CreateCompanyProfileResponse.model_validate(profile_dict)


async def update_company_profile(
    db: AsyncSession, data: UpdateCompanyProfile, current_user: User
) -> CreateCompanyProfileResponse:
    # Get the profile
    stmt = select(CompanyProfile).where(CompanyProfile.company_id == current_user.id)
    result = await db.execute(stmt)
    company_profile = result.scalar_one_or_none()

    if not company_profile:
        raise "No profile exists for this company"

    # Update values that are provided
    if company_profile:
        # Check if company name of phone number is already taken by another user
        stmt = select(CompanyProfile).where(
            CompanyProfile.company_name == data.company_name,
            CompanyProfile.phone_number == data.phone_number,
            User.id != current_user.id,
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise "Company name or phone number already registered"
        company_profile.company_name = data.company_name
        company_profile.address = data.address
        company_profile.phone_number = data.phone_number

    # Save changes
    await db.commit()
    await db.refresh(company_profile)

    return company_profile


async def update_company_payment_gateway(
    db: AsyncSession, data: UpdateCompanyPaymentGateway, current_user: User
) -> MessageResponse:
    # Get the profile
    stmt = select(CompanyProfile).where(CompanyProfile.company_id == current_user.id)
    result = await db.execute(stmt)
    company_profile = result.scalar_one_or_none()

    if not company_profile:
        raise Exception("No profile exists for this company")

    # Update values that are provided
    if company_profile:
        company_profile.api_key = encrypt_data(data.api_key)
        company_profile.api_secret = encrypt_data(data.api_secret)
        company_profile.payment_gateway = data.payment_gateway

    # Save changes
    await db.commit()
    await db.refresh(company_profile)

    msg = {"message": "Payment gateway information updated"}

    return MessageResponse(**msg)


async def create_staff_role(
    current_user: User,
    data: StaffRoleCreate,
    db: AsyncSession,
):
    """Adds existing NavItems to a Department."""
    check_permission(current_user, required_permission="create_departments")

    try:
        # First check if department with this name already exists for the company
        existing_stmt = select(Role).where(
            Role.name == data.name.lower(), Role.company_id == current_user.id
        )
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A role with this name '{data.name}' already exists for this company",
            )

        # Create Department
        role = Role(
            name=data.name.lower(),
            company_id=current_user.id,
        )

        # Add department to database
        db.add(role)
        await db.flush()
        await db.refresh(role)

        # Prepare a list for explicitly loaded nav_items
        permissions_data = []

        # Fetch and add the NavItems if they exist
        if data.permissions and len(data.permissions) > 0:
            # Use a proper async query to get all permission at once
            stmt = select(Permission).where(Permission.id.in_(data.permissions))
            result = await db.execute(stmt)
            permissions = result.scalars().all()

            # Check if all requested permissions were found
            found_ids = {permission.id for permission in permissions}
            missing_ids = set(data.permissions) - found_ids

            if missing_ids:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission(s) with id(s) {', '.join(str(id) for id in missing_ids)} not found",
                )

            # Add the permissions to the role
            role.permissions.extend(permissions)
            await db.flush()  # Ensure the relationship is saved

            # Collect data for each permission to include in response
            permissions_data = [
                {
                    "id": permission.id,
                    "name": permission.name,
                    "description": permission.description,
                }
                for permission in permissions
            ]

        await db.commit()

        # Create a fully loaded response object
        response_role = {
            "id": role.id,
            "name": role.name,
            "company_id": str(role.company_id),
            "permissions": permissions,
        }

        return response_role

    except HTTPException:
        # Re-raise HTTPException as it's already properly formatted
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def update_role_with_permissions(
    role_id: int, db: AsyncSession, data: AddPermissionsToRole, current_user: User
) -> RolePermissionResponse:
    """
    Update permissions for a company-specific role.
    Maintains security by ensuring the role belongs to the current user's company.
    """
    try:
        # Get the role with company validation
        stmt = select(Role).where(
            Role.company_id == current_user.id, Role.id == role_id
        )
        result = await db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found or doesn't belong to your company",
            )

        # Validate and collect permissions
        valid_permissions = []
        for permission_name in data.permissions:
            permission = await get_permission_by_name(name=permission_name, db=db)
            if not permission:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid permission: {permission_name}",
                )
            valid_permissions.append(permission_name)

        # Update permissions
        role.user_permissions = valid_permissions
        # role.updated_at = datetime.now()

        await db.commit()
        await db.refresh(role)

        return role

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role permissions: {str(e)}",
        )


async def get_all_permissions(db: AsyncSession) -> list[PermissionResponse]:
    result = await db.execute(select(Permission))
    return result.scalars().all()


async def get_company_staff_role(
    role_id: int, db: AsyncSession, current_user: User
) -> RoleCreateResponse:
    result = await db.execute(
        select(Role).where(Role.company_id == current_user.id, Role.id == role_id)
    )
    return result.scalar_one_or_none()


async def get_all_company_staff_roles(
    db: AsyncSession, current_user: User
) -> list[RoleCreateResponse]:
    result = await db.execute(select(Role).where(Role.company_id == current_user.id))
    return result.scalars().all()


async def create_department(
    current_user: User,
    data: DepartmentCreate,
    db: AsyncSession,
):
    """Adds existing NavItems to a Department."""
    check_permission(current_user, required_permission="create_departments")

    try:
        # First check if department with this name already exists for the company
        existing_stmt = select(Department).where(
            Department.name == data.name.lower(),
            Department.company_id == current_user.id,
        )
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A department with this name '{data.name}' already exists for this company",
            )

        # Create Department
        department = Department(
            name=data.name.lower(),
            company_id=current_user.id,
        )

        # Add department to database
        db.add(department)
        await db.flush()
        await db.refresh(department)

        # Prepare a list for explicitly loaded nav_items
        nav_items_data = []

        # Fetch and add the NavItems if they exist
        if data.nav_items and len(data.nav_items) > 0:
            # Use a proper async query to get all nav items at once
            stmt = select(NavItem).where(NavItem.id.in_(data.nav_items))
            result = await db.execute(stmt)
            nav_items = result.scalars().all()

            # Check if all requested nav_items were found
            found_ids = {item.id for item in nav_items}
            missing_ids = set(data.nav_items) - found_ids

            if missing_ids:
                await db.rollback()  # Important to rollback before raising
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"NavItem(s) with id(s) {', '.join(str(id) for id in missing_ids)} not found",
                )

            # Add the nav_items to the department
            department.nav_items.extend(nav_items)
            await db.flush()  # Ensure the relationship is saved

            # Collect data for each nav_item to include in response
            nav_items_data = [
                {
                    "id": nav_item.id,
                    "path_name": nav_item.path_name,
                    "path": nav_item.path,
                }
                for nav_item in nav_items
            ]

        await db.commit()

        # Create a fully loaded response object
        response_dept = {
            "id": department.id,
            "name": department.name,
            "company_id": str(department.company_id),
            "nav_items": nav_items_data,
        }

        return response_dept

    except HTTPException:
        # Re-raise HTTPException as it's already properly formatted
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def get_company_departments(
    current_user: User, db: AsyncSession
) -> list[DepartmentResponse]:
    company_id = get_company_id(current_user)
    stmt = select(Department).where(Department.company_id == company_id)
    result = await db.execute(stmt)
    departments = result.unique().scalars().all()

    return [DepartmentResponse.model_validate(department) for department in departments]


async def get_nav_items(db: AsyncSession) -> list[NavItemResponse]:
    stmt = select(NavItem)
    result = await db.execute(stmt)
    nav_items = result.scalars().all()

    return [NavItemResponse.model_validate(nav_item) for nav_item in nav_items]


async def delete_company_department(
    department_id: int, current_user: User, db: AsyncSession
) -> None:
    # Check permission
    check_permission(current_user, required_permission="delete_departments")

    # Determine company ID
    company_id = get_company_id(current_user)

    # Find the department
    stmt = select(Department).where(
        (Department.company_id == company_id) & (Department.id == department_id)
    )
    result = await db.execute(stmt)
    department = result.scalar_one_or_none()

    # Check if department exists
    if not department:
        raise HTTPException(
            status_code=404, detail=f"Department with ID {department_id} not found"
        )

    # Delete the department
    await db.delete(department)
    await db.commit()

    return None


async def create_no_post_list(
    data: NoPostCreate, current_user: User, db: AsyncSession
) -> NoPostResponse:
    company_id = get_company_id(current_user)
    no_post_list = NoPost(
        no_post_list=data.name.lower(),
        company_id=company_id,
    )

    stmt = select(NoPost).where(NoPost.company_id == company_id)
    existing = await db.execute(stmt)
    existing_record = existing.scalar_one_or_none()

    if existing_record:
        # Update the existing record
        existing_record.no_post_list = data.no_post_list

        await db.commit()
        await db.refresh(existing_record)
        return existing_record
    else:
        # Create a new record
        no_post_list = NoPost(
            no_post_list=data.no_post_list,
            company_id=company_id,
        )

        db.add(no_post_list)
        await db.commit()
        await db.refresh(no_post_list)

        return no_post_list


async def get_company_no_post_list(
    current_user: User, db: AsyncSession
) -> list[NoPostResponse]:
    company_id = get_company_id(current_user)
    stmt = select(NoPost).where(NoPost.company_id == company_id)
    result = await db.execute(stmt)
    no_post_list = result.unique().scalars().all()

    return no_post_list


async def create_outlet(
    current_user: User, data: OutletCreate, db: AsyncSession
) -> OutleResponse:
    check_permission(current_user, required_permission="create_outlets")

    try:
        outlet = Outlet(
            name=data.name.lower(),
            company_id=current_user.id,
        )

        # Add outlet to database
        db.add(outlet)
        await db.commit()
        await db.refresh(outlet)

        return outlet

    except Exception as e:
        error_detail = str(e)

        if "outlet_name" in error_detail:
            # Extract the key and value from the error message
            key_match = re.search(r"Key \((\w+)\)=\((\w+)\)", error_detail)
            if key_match:
                key, value = key_match.groups()
                raise Exception(
                    f"Outlet with this {key} '{value}' already exists for this company"
                )


async def get_company_outlets(
    current_user: User, db: AsyncSession
) -> list[DepartmentResponse]:
    company_id = get_company_id(current_user)

    stmt = select(Outlet).where(Outlet.company_id == company_id)
    result = await db.execute(stmt)
    outlets = result.all()

    return outlets


async def delete_company_outlet(
    outlet_id: int, current_user: User, db: AsyncSession
) -> None:
    # Check permission
    check_permission(current_user, required_permission="delete_outlets")

    # Determine company ID
    company_id = get_company_id(current_user)

    # Find the outlet
    stmt = select(Outlet).where(
        (Outlet.company_id == company_id) & (Outlet.id == outlet_id)
    )
    result = await db.execute(stmt)
    outlet = result.scalar_one_or_none()

    # Check if outlet exists
    if not outlet:
        raise HTTPException(
            status_code=404, detail=f"Outlet with ID {outlet_id} not found"
        )

    # Delete the outlet
    await db.delete(outlet)
    await db.commit()

    return None


async def create_rate(
    data: RatetCreate, current_user: User, db: AsyncSession
) -> RatetResponse:
    await check_permission(user=current_user, required_permission="create_rate")
    company_id = get_company_id(current_user)
    try:
        # Create a new rate
        rate = Rate(
            name=data.name,
            pay_type=data.pay_type,
            rate_amount=data.rate_amount,
            company_id=company_id,
        )

        db.add(rate)
        await db.commit()
        await db.refresh(rate)

        return rate
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


async def get_company_rates(
    current_user: User, db: AsyncSession
) -> list[RatetResponse]:
    # Determine company ID
    company_id = get_company_id(current_user)

    # Find company rates
    stmt = select(Rate).where((Rate.company_id == company_id))
    result = await db.execute(stmt)
    company_rates = result.unique().scalars().all()

    return company_rates


async def delete_company_rate(
    rate_id: int, current_user: User, db: AsyncSession
) -> None:
    # Check permission
    await check_permission(current_user, required_permission="delete_rate")

    # Determine company ID
    company_id = get_company_id(current_user)

    # Find the rate
    stmt = select(Rate).where(Rate.id == rate_id).where(Rate.company_id == company_id)
    result = await db.execute(stmt)
    rate = result.scalar_one_or_none()

    # Check if rate exists
    if not rate:
        raise HTTPException(status_code=404, detail=f"Rate with ID {rate_id} not found")

    # Delete the rate
    await db.delete(rate)
    await db.commit()

    return None
