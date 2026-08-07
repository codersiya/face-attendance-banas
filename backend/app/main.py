# """
# FastAPI application entrypoint.

# Dev run:
#     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production run (behind a process manager / reverse proxy):
#     uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
# """
# import logging

# from fastapi import FastAPI, Request, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse

# from app.config import settings
# from app.database import Base, engine
# from app.routers import employees

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s %(levelname)s %(name)s: %(message)s",
# )
# logger = logging.getLogger("app.main")

# app = FastAPI(
#     title="Face Attendance Enrollment API",
#     description="Employee enrollment with face embeddings for attendance tracking.",
#     version="1.0.0",
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=settings.allowed_origins_list,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# @app.on_event("startup")
# def on_startup():
#     if settings.is_production:
#         # In production, schema changes go through Alembic migrations
#         # (see alembic/ directory) - never via implicit create_all(), which
#         # can silently diverge from what migrations expect.
#         logger.info("Production mode: skipping create_all(). Run 'alembic upgrade head' separately.")
#     else:
#         Base.metadata.create_all(bind=engine)
#         logger.info("Dev mode: ensured tables exist via create_all().")


# @app.exception_handler(Exception)
# async def unhandled_exception_handler(request: Request, exc: Exception):
#     logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "An unexpected error occurred. Please try again or contact support."},
#     )


# @app.get("/health", tags=["health"])
# def health_check():
#     return {"status": "ok"}


# app.include_router(employees.router)




































"""
FastAPI application entrypoint.

Dev run:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Production run (behind a process manager / reverse proxy):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

Frontend serving:
    In Docker (see Dockerfile), nginx serves the built frontend and proxies
    /api/* to this app on :8000 - so normally this app only needs to answer
    API routes. The optional static mount below is a fallback for running
    the backend standalone (no nginx) against a local `frontend/dist`
    build, e.g. for quick local prod-mode testing. It's a no-op if that
    directory doesn't exist.
"""
import logging
import logging.config
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import employees

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# - Everything goes through one formatter so app logs and uvicorn's own logs
#   look the same.
# - Level is driven by ENVIRONMENT: verbose in dev, quieter in production.
# - SQLAlchemy's engine logger is explicitly tamed - it's extremely chatty
#   at INFO (logs every SQL statement) if left at the root level.
LOG_LEVEL = "DEBUG" if not settings.is_production else "INFO"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Quiet down libraries that are noisy at DEBUG/INFO.
        "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
        "uvicorn.access": {"level": "INFO", "propagate": True},
        "watchfiles": {"level": "WARNING", "propagate": True},
        # Our own app code - always informative.
        "app": {"level": LOG_LEVEL, "propagate": True},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app.main")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Face Attendance Enrollment API",
    description="Employee enrollment with face embeddings for attendance tracking.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    if settings.is_production:
        # In production, schema changes go through Alembic migrations
        # (see alembic/ directory) - never via implicit create_all(), which
        # can silently diverge from what migrations expect.
        logger.info("Production mode: skipping create_all(). Run 'alembic upgrade head' separately.")
    else:
        Base.metadata.create_all(bind=engine)
        logger.info("Dev mode: ensured tables exist via create_all().")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again or contact support."},
    )


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# API routes must be registered before the SPA catch-all below, or the
# catch-all would shadow them.
app.include_router(employees.router)


# ---------------------------------------------------------------------------
# Frontend (SPA) serving - optional, see module docstring.
# ---------------------------------------------------------------------------
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    logger.info("Serving frontend build from %s", FRONTEND_DIST)

    # Serves hashed JS/CSS/etc under /assets/*.
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        Catch-all for client-side (React Router) routes: any path that
        isn't an API route or a known static asset gets index.html, so
        that e.g. reloading the browser on /employees/123 works instead
        of 404ing.
        """
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    logger.info(
        "No frontend build found at %s - skipping SPA static mount "
        "(expected when nginx serves the frontend, e.g. in Docker).",
        FRONTEND_DIST,
    )