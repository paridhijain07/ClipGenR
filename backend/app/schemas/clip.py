from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WordTimestampRead(BaseModel):
    id: Optional[str] = None
    word: str
    start_time: float
    end_time: float
    confidence: float = 1.0
    word_index: int

    class Config:
        from_attributes = True


class ClipCaptionRead(BaseModel):
    id: str
    preset_name: str
    font_family: str
    font_size: int
    primary_color: str
    highlight_color: str
    stroke_color: str
    stroke_width: int
    position: str
    custom_words_json: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class ClipCaptionUpdate(BaseModel):
    preset_name: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    primary_color: Optional[str] = None
    highlight_color: Optional[str] = None
    stroke_color: Optional[str] = None
    stroke_width: Optional[int] = None
    position: Optional[str] = None
    custom_words_json: Optional[List[Dict[str, Any]]] = None


class GeneratedClipRead(BaseModel):
    id: str
    video_id: str
    title: str
    summary: Optional[str] = None
    hook_text: Optional[str] = None
    topic_tag: str
    start_time: float
    end_time: float
    duration_seconds: float
    engagement_score: float
    score_breakdown: Dict[str, Any]
    aspect_ratio: str
    storage_key: Optional[str] = None
    thumbnail_key: Optional[str] = None
    status: str
    created_at: datetime
    captions: Optional[ClipCaptionRead] = None
    video_source_url: Optional[str] = None

    class Config:
        from_attributes = True


class GeneratedClipUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[float] = Field(None, ge=0.0)
    end_time: Optional[float] = Field(None, ge=0.0)
    aspect_ratio: Optional[str] = None


class ExportRead(BaseModel):
    id: str
    clip_id: str
    export_format: str
    resolution: str
    file_size_bytes: int
    download_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
