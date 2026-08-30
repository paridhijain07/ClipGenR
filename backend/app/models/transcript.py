from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.models.base import TimeStampedModel


class Transcript(TimeStampedModel):
    __tablename__ = "transcripts"

    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_text = Column(Text, nullable=False)
    language = Column(String(20), default="en", nullable=False)
    total_words = Column(Integer, default=0, nullable=False)
    raw_payload = Column(JSON, default=dict)

    video = relationship("Video", back_populates="transcript")
    words = relationship("TranscriptWord", back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptWord.word_index.asc()")


class TranscriptWord(TimeStampedModel):
    __tablename__ = "transcript_words"

    transcript_id = Column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False, index=True)
    word = Column(String(100), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    word_index = Column(Integer, nullable=False)

    transcript = relationship("Transcript", back_populates="words")
