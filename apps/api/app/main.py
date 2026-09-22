from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles

from app.admin_operations.router import public_router as moderation_router
from app.admin_operations.router import router as admin_operations_router
from app.auth.router import admin_router
from app.auth.router import router as auth_router
from app.community.router import admin_router as community_admin_router
from app.community.router import router as community_router
from app.config import get_settings
from app.leaderboards.router import leaderboard_router, social_router
from app.learning.router import admin_router as learning_admin_router
from app.learning.router import router as learning_router
from app.learning_engine.router import router as learning_engine_router
from app.notifications.router import router as notifications_router

settings = get_settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Request-ID"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(community_router, prefix=settings.api_prefix)
app.include_router(community_admin_router, prefix=settings.api_prefix)
app.include_router(admin_operations_router, prefix=settings.api_prefix)
app.include_router(moderation_router, prefix=settings.api_prefix)
app.include_router(learning_router, prefix=settings.api_prefix)
app.include_router(learning_engine_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.include_router(learning_admin_router, prefix=settings.api_prefix)
app.include_router(leaderboard_router, prefix=settings.api_prefix)
app.include_router(social_router, prefix=settings.api_prefix)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", environment=settings.app_env)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "request_id": request.headers.get("X-Request-ID"),
            }
        },
    )
