from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import uuid

from app.models.models import User, RefreshToken
from app.schemas.user_schema import TokenResponse
from app.database.database import get_db
from app.config.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def create_refresh_token(user_id: str, db: AsyncSession) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        token=token, user_id=user_id, expires_at=expires_at)

    db.add(refresh_token)
    await db.commit()

    return token


async def create_tokens(user_id: str, db: AsyncSession) -> TokenResponse:
    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = await create_refresh_token(user_id, db)

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


async def verify_refresh_token(token: str, db: AsyncSession) -> str:
    result = await db.execute(
        "SELECT user_id, expires_at, is_revoked FROM refresh_tokens WHERE token = :token",
        {"token": token},
    )
    row = result.fetchone()

    if not row:
        return None

    user_id, expires_at, is_revoked = row

    if is_revoked or expires_at < datetime.utcnow():
        return None

    return user_id


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, str(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


async def revoke_refresh_token(token: str, db: AsyncSession) -> bool:
    result = await db.execute(
        "UPDATE refresh_tokens SET is_revoked = TRUE WHERE token = :token RETURNING id",
        {"token": token},
    )
    row = result.fetchone()
    await db.commit()

    return row is not None
