from contextlib import asynccontextmanager
from fastapi import FastAPI
import logfire
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from app.database.database import AsyncSessionLocal, engine
from app.config.config import settings

from app.routes import (
    auth_router,
    event_router,
    qrcode_router,
    reservation_router,
    staff_attendance_routes,
    user_router,
    item_router,
    order_router,
    payroll_routes,
    staff_attendance_routes,
    # notification_routes
)
from app.services.profile_service import pre_create_permissions, setup_company_roles
from app.services.qrcode_service import initialize_qr_code_limits


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await pre_create_permissions(db)
        await initialize_qr_code_limits(db)
    yield


app = FastAPI(
    title="MOHspitality",
    docs_url="/",
    lifespan=lifespan,
    description="Complete hospitality solutions",
    summary="QRCode food ordering, staff management, restaurant management and more...",
)


limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# configure logfire
logfire.configure(token=settings.LOGFIRE_TOKEN)
logfire.instrument_sqlalchemy(engine=engine)
logfire.instrument_fastapi(app, capture_headers=True)


app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(qrcode_router.router)
app.include_router(item_router.router)
app.include_router(order_router.router)
app.include_router(event_router.router)
app.include_router(reservation_router.router)
app.include_router(payroll_routes.router)
app.include_router(staff_attendance_routes.router)
# app.include_router(notification_routes.router)


# Allow requests from your frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://192.168.43.188:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
