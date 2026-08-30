import enum
from sqlalchemy import BigInteger, Column, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import TimeStampedModel


class ClipStatus(str, enum.Enum):
    PENDING = "PENDING"
    READY = "READY"
    RENDERING = "RENDERING"
    FAILED = "FAILED"


class GeneratedClip(TimeStampedModel):
    __tablename__ = "generated_clips"

    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    hook_text = Column(Text, nullable=True)
    topic_tag = Column(String(100), default="General", nullable=False)
    
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    # 7-factor scoring
    engagement_score = Column(Float, default=0.0, nullable=False, index=True)
    score_breakdown = Column(JSON, default=dict)
    
    aspect_ratio = Column(String(20), default="9:16", nullable=False)
    storage_key = Column(String(512), nullable=True)
    thumbnail_key = Column(String(512), nullable=True)
    status = Column(String(50), default=ClipStatus.READY.value, nullable=False)
    
    # Relationships
    video = relationship("Video", back_populates="clips")
    captions = relationship("ClipCaption", back_populates="clip", uselist=False, cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="clip", cascade="all, delete-orphan")


class ClipCaption(TimeStampedModel):
    __tablename__ = "clip_captions"

    clip_id = Column(String(36), ForeignKey("generated_clips.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    preset_name = Column(String(50), default="hormozi_yellow", nullable=False)
    font_family = Column(String(100), default="Inter", nullable=False)
    font_size = Column(Integer, default=48, nullable=False)
    primary_color = Column(String(20), default="#FFFFFF", nullable=False)
    highlight_color = Column(String(20), default="#FACC15", nullable=False)
    stroke_color = Column(String(20), default="#000000", nullable=False)
    stroke_width = Column(Integer, default=3, nullable=False)
    position = Column(String(20), default="bottom", nullable=False)  # top, center, bottom
    
    # Custom edited word tokens (optional override of original transcript)
    custom_words_json = Column(JSON, default=list)

    clip = relationship("GeneratedClip", back_populates="captions")


class Export(TimeStampedModel):
    __tablename__ = "exports"

    clip_id = Column(String(36), ForeignKey("generated_clips.id", ondelete="CASCADE"), nullable=False, index=True)
    export_format = Column(String(20), default="mp4", nullable=False)
    resolution = Column(String(20), default="1080x1920", nullable=False)
    storage_key = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger, default=0, nullable=False)
    download_url = Column(String(1024), nullable=True)

    clip = relationship("GeneratedClip", back_populates="exports")
