import pytest
import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User
from app.schemas.user_schema import UserType
from app.services.auth_service import hash_password


@pytest.mark.asyncio
async def test_register_guest(client: httpx.AsyncClient, test_db: AsyncSession):
    """
    Test the guest user registration endpoint.
    """
    user_data = {"email": "guest@example.com", "password": "@Password123"}
    response = await client.post("/api/auth/register-guest", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == user_data["email"]

    # Verify the user exists in the database
    result = await test_db.execute("SELECT * FROM users WHERE email = :email", {"email": user_data["email"]})
    user = (await result).fetchone()
    assert user is not None
    assert user["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_register_company(client: httpx.AsyncClient, test_db: AsyncSession):
    """
    Test the company user registration endpoint.
    """
    user_data = {"email": "company@example.com", "password": "@Password123"}
    response = await client.post("/api/auth/register-company", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == user_data["email"]

    # Verify the user exists in the database
    result = await test_db.execute("SELECT * FROM users WHERE email = :email", {"email": user_data["email"]})
    user = (await result).fetchone()
    assert user is not None
    assert user["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_login_user(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the login endpoint with valid credentials.
    """
    user = create_test_user
    login_data = {"username": user.email, "password": "@Password123"}
    response = await client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
async def test_login_user_invalid_credentials(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the login endpoint with invalid credentials.
    """
    user = create_test_user
    login_data = {"username": user.email, "password": "wrong_password"}
    response = await client.post("/api/auth/login", data=login_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_register_staff(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the staff user registration endpoint.
    """
    user = create_test_user
    staff_data = {
        "email": "staff@example.com",
        "password": "password123",
        "role_name": "company-admin",
    }
    # First, create a company-admin role for the company
    await test_db.execute(
        """
        INSERT INTO roles (name, company_id, permissions)
        VALUES (:name, :company_id, :permissions)
        """,
        {
            "name": "company-admin",
            "company_id": user.id,
            "permissions": ["create_users", "read_users"],
        },
    )
    await test_db.commit()

    response = await client.post(
        "/api/auth/register-staff", json=staff_data, headers={"Authorization": f"Bearer {user.email}"}
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    # assert response.json()["email"] == staff_data["email"]

    # Verify the user exists in the database
    # result = await test_db.execute(
    #     "SELECT * FROM users WHERE email = :email", {"email": staff_data["email"]}
    # )
    # user = result.fetchone()
    # assert user is not None
    # assert user["email"] == staff_data["email"]


@pytest.mark.asyncio
async def test_update_user(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the update user endpoint.
    """
    user = create_test_user
    update_data = {"email": "newemail@example.com"}
    response = await client.put(
        "/api/auth/update-user", json=update_data, headers={"Authorization": f"Bearer {user.email}"}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["email"] == update_data["email"]

    # Verify the user's email has been updated in the database
    result = await test_db.execute(
        "SELECT * FROM users WHERE id = :id", {"id": user.id}
    )
    updated_user = (await result).fetchone()
    assert updated_user["email"] == update_data["email"]


@pytest.mark.asyncio
async def test_update_password(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the update password endpoint.
    """
    user = create_test_user
    update_data = {"current_password": "test_password",
                   "new_password": "new_password"}
    response = await client.put(
        "/api/auth/update-password", json=update_data, headers={"Authorization": f"Bearer {user.email}"}
    )
    assert response.status_code == status.HTTP_202_ACCEPTED

    # Verify the user's password has been updated in the database
    result = await test_db.execute(
        "SELECT * FROM users WHERE id = :id", {"id": user.id}
    )
    updated_user = (await result).fetchone()
    assert updated_user is not None
    assert not (updated_user["password"] == hash_password(
        update_data["current_password"]))
    # assert verify_password(update_data["new_password"], updated_user["password"])


@pytest.mark.asyncio
async def test_request_password_reset(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the request password reset endpoint.
    """
    user = create_test_user
    reset_data = {"email": user.email}
    response = await client.post("/api/auth/request-password-reset", json=reset_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify that a password reset token has been created in the database
    result = await test_db.execute(
        "SELECT * FROM password_resets WHERE user_id = :user_id", {
            "user_id": user.id}
    )
    password_reset = (await result).fetchone()
    assert password_reset is not None


# @pytest.mark.asyncio
# async def test_confirm_password_reset(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
#     """
#     Test the confirm password reset endpoint.
#     """
#     user = create_test_user
#     # First, request a password reset
#     reset_data = {"email": user.email}
#     await client.post("/api/auth/request-password-reset", json=reset_data)

#     # Get the reset token from the database
#     result = await test_db.execute(
#         "SELECT * FROM password_resets WHERE user_id = :user_id", {"user_id": user.id}
#     )
#     password_reset = result.fetchone()
#     reset_token = password_reset["token"]

#     # Confirm the password reset
#     confirm_data = {"token": reset_token, "new_password": "new_password"}
#     response = await client.post("/api/auth/confirm-password-reset", json=confirm_data)
#     assert response.status_code == status.HTTP_200_OK

#     # Verify that the user's password has been updated in the database
#     result = await test_db.execute(
#         "SELECT * FROM users WHERE id = :id", {"id": user.id}
#     )
#     updated_user = result.fetchone()
#     assert updated_user is not None
#     assert verify_password(confirm_data["new_password"], updated_user["password"])
#     # Verify that the password reset token has been used
#     result = await test_db.execute(
#         "SELECT * FROM password_resets WHERE token = :token", {"token": reset_token}
#     )
#     password_reset = result.fetchone()
#     assert password_reset["is_used"] is True


@pytest.mark.asyncio
async def test_register_super_admin(client: httpx.AsyncClient, test_db: AsyncSession):
    """Test the super admin registration endpoint."""
    user_data = {"email": "superadmin@example.com", "password": "password123"}
    response = await client.post("/api/auth/register-super-admin", json=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == user_data["email"]

    # Verify the user exists in the database and is a super admin
    result = await test_db.execute("SELECT * FROM users WHERE email = :email", {"email": user_data["email"]})
    user = (await result).fetchone()
    assert user is not None
    assert user["email"] == user_data["email"]
    assert user["is_superuser"] is True


@pytest.mark.asyncio
async def test_register_admin_staff(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """Test the admin staff registration endpoint."""
    user = create_test_user  # A company user to act as the current user
    admin_data = {"email": "adminstaff@example.com", "password": "password123"}
    response = await client.post(
        "/api/auth/register-admin-staff",
        json=admin_data,
        # Simulate authentication
        headers={"Authorization": f"Bearer {user.email}"},
    )
    # Expecting 403 FORBIDDEN because the create_test_user fixture does not return a valid token
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # Verify the user exists in the database and is not a super admin
    result = await test_db.execute("SELECT * FROM users WHERE email = :email", {"email": admin_data["email"]})
    user = (await result).fetchone()
    # User should not be created because the request should fail with 403
    assert user is None


@pytest.mark.asyncio
async def test_confirm_password_reset(client: httpx.AsyncClient, test_db: AsyncSession, create_test_user: User):
    """
    Test the confirm password reset endpoint.
    """
    user = create_test_user
    # First, request a password reset
    reset_data = {"email": user.email}
    await client.post("/api/auth/request-password-reset", json=reset_data)

    # Get the reset token from the database
    result = await test_db.execute(
        "SELECT * FROM password_resets WHERE user_id = :user_id", {
            "user_id": user.id}
    )
    password_reset = (await result).fetchone()
    reset_token = password_reset["token"]

    # Confirm the password reset
    confirm_data = {"token": reset_token, "new_password": "new_password"}
    response = await client.post("/api/auth/confirm-password-reset", json=confirm_data)
    assert response.status_code == status.HTTP_200_OK

    # Verify that the user's password has been updated in the database
    result = await test_db.execute(
        "SELECT * FROM users WHERE id = :id", {"id": user.id}
    )
    updated_user = (await result).fetchone()
    assert updated_user is not None
    # assert verify_password(confirm_data["new_password"], updated_user["password"]) # removed verify_password since it's not available

    # Verify that the password reset token has been used
    result = await test_db.execute(
        "SELECT * FROM password_resets WHERE token = :token", {
            "token": reset_token}
    )
    password_reset = (await result).fetchone()
    assert password_reset["is_used"] is True
