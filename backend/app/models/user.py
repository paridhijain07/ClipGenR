from sqlalchemy import Boolean, Column, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from backend.app.models.base import TimeStampedModel


class User(TimeStampedModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="creator", nullable=False)  # creator, admin
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserSettings(TimeStampedModel):
    __tablename__ = "user_settings"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    default_caption_preset = Column(String(50), default="hormozi_yellow")
    default_aspect_ratio = Column(String(20), default="9:16")
    default_clip_count = Column(String(10), default="5")
    preferences = Column(JSON, default=dict)

    user = relationship("User", back_populates="settings")
