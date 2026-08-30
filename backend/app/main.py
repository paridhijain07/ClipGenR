import sys
from pathlib import Path

# Ensure workspace root is in python path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.core.logging import logger, setup_logging
# Import all models to ensure metadata registration
import backend.app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    # Setup structured logging
    setup_logging(settings.ENVIRONMENT)
    logger.info("Initializing ClipGenR AI application", environment=settings.ENVIRONMENT, version=settings.VERSION)

    # Auto-create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema synchronized successfully")
        
        # Pre-seed default creator user
        from backend.app.core.database import SessionLocal
        from backend.app.models.user import User, UserSettings
        from backend.app.core.security import get_password_hash
        db = SessionLocal()
        try:
            if not db.query(User).filter(User.email == "creator@clipgenr.ai").first():
                user = User(
                    email="creator@clipgenr.ai",
                    hashed_password=get_password_hash("creator123!"),
                    full_name="ClipGenR Creator",
                    role="creator",
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                db.add(UserSettings(user_id=user.id))
                db.commit()
                logger.info("Default creator user provisioned")
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to initialize database tables", error=str(e))

    # Ensure storage directories exist
    storage_root = Path(settings.STORAGE_LOCAL_DIR).resolve()
    for subdir in ["videos", "audio", "thumbnails", "thumbnails/clips", "exports"]:
        (storage_root / subdir).mkdir(parents=True, exist_ok=True)
    logger.info("Storage directory structure verified", storage_path=str(storage_root))

    yield

    logger.info("Shutting down ClipGenR AI application")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "storage": settings.STORAGE_PROVIDER,
        "database": "connected",
    }


# Include API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
