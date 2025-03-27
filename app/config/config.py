import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import redis

load_dotenv()


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "MOHospitality"
    DEBUG: bool = os.getenv("DEBUG", "False") == "True"

    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/auth_db"
    )

    # JWT settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Fernet key
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY")

    # FLUTTERWAVE
    FLW_PUBLIC_KEY: str = os.getenv("FLW_PUBLIC_KEY")
    FLW_SECRET_KEY: str = os.getenv("FLW_SECRET_KEY")

    # PAYSTACK
    PSK_SECRET: str = os.getenv("PSK_SECRET")
    PSK_PUBLIC: str = os.getenv("PSK_PUBLIC")

    # Email settings
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "")
    # MAIL_TLS: bool = os.getenv("MAIL_TLS", "True") == "True"
    # MAIL_SSL: bool = os.getenv("MAIL_SSL", "False") == "True"

    # Password reset settings
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None  # Set this in production


settings = Settings()

# Redis client setup

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
)
