import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String
from backend.app.core.database import Base


def generate_uuid_str() -> str:
    return str(uuid.uuid4())


class TimeStampedModel(Base):
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=generate_uuid_str, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
