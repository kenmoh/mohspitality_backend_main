import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config.config import settings
from app.database.database import Base, get_db
from app.main import app
from app.models.models import User
from app.services.auth_service import hash_password

# Override settings for testing
settings.DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")

# Create async engine for testing
test_engine = create_async_engine(
    settings.DATABASE_URL, echo=False, poolclass=NullPool)
TestAsyncSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False)


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Override the get_db dependency to use the test database.
    """
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_database():
    """
    Create and drop the test database for the entire test session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a new session for each test function.
    """
    async with TestAsyncSessionLocal() as session:
        yield session
        # Rollback the session after each test to ensure a clean state
        await session.rollback()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create a new httpx client instance for each test function.
    """
    app.dependency_overrides[get_db] = get_test_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def create_test_user(test_db: AsyncSession) -> User:
    """
    Create a test user for testing purposes.
    """
    user_data = {
        "email": "test@example.com",
        "password": "test_password",
        "user_type": "COMPANY",
        "is_active": True,
        "is_superuser": False,
        "updated_at": "2024-10-24T11:00:00"
    }
    user = User(
        email=user_data["email"],
        password=hash_password(user_data["password"]),
        user_type=user_data["user_type"],
        is_active=user_data["is_active"],
        is_superuser=user_data["is_superuser"],
        updated_at=user_data["updated_at"],
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user
