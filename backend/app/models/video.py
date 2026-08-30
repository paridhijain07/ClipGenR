import enum
from sqlalchemy import BigInteger, Column, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import TimeStampedModel


class VideoStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStage(str, enum.Enum):
    QUEUED = "QUEUED"
    EXTRACTING_AUDIO = "EXTRACTING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING_SEMANTICS = "ANALYZING_SEMANTICS"
    RANKING_CLIPS = "RANKING_CLIPS"
    CROPPING_RENDERING = "CROPPING_RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Video(TimeStampedModel):
    __tablename__ = "videos"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False)
    audio_storage_key = Column(String(512), nullable=True)
    thumbnail_key = Column(String(512), nullable=True)
    
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=True, default=0.0)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    fps = Column(Float, nullable=True)
    codec = Column(String(50), nullable=True)
    
    status = Column(String(50), default=VideoStatus.PENDING.value, nullable=False, index=True)
    
    # Relationships
    owner = relationship("User", back_populates="videos")
    jobs = relationship("ProcessingJob", back_populates="video", cascade="all, delete-orphan", order_by="ProcessingJob.created_at.desc()")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    clips = relationship("GeneratedClip", back_populates="video", cascade="all, delete-orphan")


class ProcessingJob(TimeStampedModel):
    __tablename__ = "processing_jobs"

    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), default=JobStage.QUEUED.value, nullable=False)
    progress_percent = Column(Integer, default=0, nullable=False)
    stage_description = Column(String(255), default="Job is queued in processing line", nullable=False)
    
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    job_metadata = Column(JSON, default=dict)
    
    video = relationship("Video", back_populates="jobs")
