from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VideoUploadIntentRequest(BaseModel):
    filename: str
    file_size_bytes: int = Field(..., gt=0)
    mime_type: str
    title: Optional[str] = None


class VideoUploadIntentResponse(BaseModel):
    video_id: str
    upload_url: Optional[str] = None  # Pre-signed S3 URL or direct upload path
    storage_key: str
    direct_upload: bool = True


class ProcessingJobRead(BaseModel):
    id: str
    video_id: str
    stage: str
    progress_percent: int
    stage_description: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    job_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoRead(BaseModel):
    id: str
    user_id: str
    title: str
    original_filename: str
    file_size_bytes: int
    duration_seconds: Optional[float] = 0.0
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    status: str
    thumbnail_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    active_job: Optional[ProcessingJobRead] = None
    clip_count: Optional[int] = 0

    class Config:
        from_attributes = True


class VideoDetailRead(VideoRead):
    jobs: List[ProcessingJobRead] = []
