from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.employee_profile.router import router as employee_profile_router
from app.prio_integration.router import router as prio_integration_router

app = FastAPI(title="FDE Performance Review & Resource Visibility Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Map every typed AppError to its safe, generic client-facing body."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Never let an unexpected error's message or stack trace reach the client."""
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})


app.include_router(auth_router)
app.include_router(employee_profile_router)
app.include_router(prio_integration_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check; returns the running environment."""
    return {"status": "ok", "environment": settings.environment}
