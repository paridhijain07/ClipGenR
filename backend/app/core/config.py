import os
from pathlib import Path
from typing import List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

# Ensure HuggingFace and PyTorch caches are stored in workspace directory with ample disk space
_WORKSPACE_CACHE = Path(__file__).resolve().parent.parent.parent.parent / ".cache"
_WORKSPACE_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_WORKSPACE_CACHE / "huggingface"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(_WORKSPACE_CACHE / "huggingface" / "hub"))
os.environ.setdefault("TORCH_HOME", str(_WORKSPACE_CACHE / "torch"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class Settings(BaseModel):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "ClipGenR AI")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-production-min32chars")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./clipforge.db")

    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: Optional[str] = os.getenv("CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = os.getenv("CELERY_RESULT_BACKEND")

    # Storage (local or s3)
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    STORAGE_LOCAL_DIR: str = os.getenv("STORAGE_LOCAL_DIR", "./storage_data")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "clipgenr-assets")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_ACCESS_KEY: Optional[str] = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY: Optional[str] = os.getenv("S3_SECRET_KEY")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")

    # Upload Constraints
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(2 * 1024 * 1024 * 1024)))
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".mkv", ".webm", ".avi"]
    ALLOWED_MIME_TYPES: List[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-matroska",
        "video/webm",
        "video/x-msvideo",
    ]

    # AI Model Providers
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")


settings = Settings()
