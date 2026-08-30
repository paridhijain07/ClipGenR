from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.security import decode_token
from backend.app.models.user import User
from backend.app.services.storage.base import BaseStorageService
from backend.app.services.storage.local import LocalStorageService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

_storage_instance: Optional[BaseStorageService] = None


def get_db() -> Generator[Session, None, None]:
    """Database session generator dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_storage_service() -> BaseStorageService:
    """Storage service singleton dependency."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalStorageService(settings.STORAGE_LOCAL_DIR)
    return _storage_instance


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """Validate JWT token and return authenticated User, or create/return default demo creator."""
    if token:
        payload = decode_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user

    # Seamless fallback for single-user dev/demo environment:
    default_user = db.query(User).filter(User.email.in_(["creator@clipgenr.ai", "creator@clipforge.ai"])).first()
    if not default_user:
        try:
            from backend.app.core.security import get_password_hash
            default_user = User(
                email="creator@clipgenr.ai",
                hashed_password=get_password_hash("creator123!"),
                full_name="ClipGenR Creator",
                role="creator",
                is_active=True,
                is_verified=True,
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        except Exception:
            db.rollback()
            default_user = db.query(User).filter(User.email.in_(["creator@clipgenr.ai", "creator@clipforge.ai"])).first()

    return default_user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    return current_user
