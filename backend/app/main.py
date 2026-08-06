"""
FastAPI application entrypoint.

Dev run:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Production run (behind a process manager / reverse proxy):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import employees

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

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


app.include_router(employees.router)