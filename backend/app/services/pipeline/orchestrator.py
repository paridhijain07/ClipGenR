import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.clip import ClipCaption, GeneratedClip, ClipStatus
from backend.app.models.transcript import Transcript, TranscriptWord
from backend.app.models.video import JobStage, ProcessingJob, Video, VideoStatus
from backend.app.services.ai.analyzer import viral_analyzer_service
from backend.app.services.ai.transcription import transcription_service
from backend.app.services.caption.caption_engine import caption_engine
from backend.app.services.storage.local import LocalStorageService
from backend.app.services.video.ffmpeg_service import ffmpeg_service


class PipelineOrchestrator:
    """End-to-end processing pipeline orchestrator for video analysis, clipping, and captioning."""

    def __init__(self, storage_service: Optional[LocalStorageService] = None):
        self.storage = storage_service or LocalStorageService()

    def process_video(self, db: Session, video_id: str, job_id: Optional[str] = None) -> bool:
        """
        Execute the full video clipping pipeline synchronously inside background worker.
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error("Pipeline failed: Video not found", video_id=video_id)
            return False

        job = None
        if job_id:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            job = db.query(ProcessingJob).filter(ProcessingJob.video_id == video_id).order_by(ProcessingJob.created_at.desc()).first()
            if not job:
                job = ProcessingJob(
                    video_id=video_id,
                    stage=JobStage.QUEUED.value,
                    progress_percent=0,
                    stage_description="Initializing processing pipeline",
                )
                db.add(job)
                db.commit()
                db.refresh(job)

        try:
            # 1. Update status to PROCESSING
            video.status = VideoStatus.PROCESSING.value
            self._update_job(db, job, JobStage.EXTRACTING_AUDIO, 10, "Extracting audio and inspecting video streams")

            local_video_path = self.storage.get_file_path_or_url(video.storage_key)

            # Probe video metadata
            meta = ffmpeg_service.get_video_metadata(local_video_path)
            video.duration_seconds = meta.get("duration", 0.0)
            video.width = meta.get("width", 1920)
            video.height = meta.get("height", 1080)
            video.fps = meta.get("fps", 30.0)
            video.codec = meta.get("codec", "h264")
            db.commit()

            # Extract main video thumbnail
            thumb_key = f"thumbnails/{video.id}_thumb.jpg"
            thumb_path = self.storage.get_file_path_or_url(thumb_key)
            if ffmpeg_service.extract_thumbnail(local_video_path, thumb_path, timestamp_sec=min(2.0, video.duration_seconds or 1.0)):
                video.thumbnail_key = thumb_key
                db.commit()

            # Extract 16kHz audio
            audio_key = f"audio/{video.id}_audio.wav"
            audio_path = self.storage.get_file_path_or_url(audio_key)
            audio_success = ffmpeg_service.extract_audio(local_video_path, audio_path)
            if not audio_success:
                raise RuntimeError("Failed to extract audio track from source video")
            video.audio_storage_key = audio_key
            db.commit()

            # 2. Transcribe Audio
            self._update_job(db, job, JobStage.TRANSCRIBING, 30, "Transcribing speech into word-level timestamps")
            transcript_result = transcription_service.transcribe_audio(audio_path)

            # Save transcript and words to database
            # Remove any previous transcript for this video
            db.query(Transcript).filter(Transcript.video_id == video.id).delete()
            db.commit()

            transcript_record = Transcript(
                video_id=video.id,
                full_text=transcript_result["full_text"],
                language=transcript_result.get("language", "en"),
                total_words=len(transcript_result.get("words", [])),
                raw_payload=transcript_result.get("raw_payload", {}),
            )
            db.add(transcript_record)
            db.commit()
            db.refresh(transcript_record)

            # Insert words
            words_to_add = []
            for w in transcript_result.get("words", []):
                words_to_add.append(
                    TranscriptWord(
                        transcript_id=transcript_record.id,
                        word=w["word"],
                        start_time=w["start_time"],
                        end_time=w["end_time"],
                        confidence=w.get("confidence", 1.0),
                        word_index=w["word_index"],
                    )
                )
            db.bulk_save_objects(words_to_add)
            db.commit()

            # 3. AI Semantic Analysis & Viral Hook Scoring
            self._update_job(db, job, JobStage.ANALYZING_SEMANTICS, 55, "Analyzing retention spikes and 7-factor virality matrix")
            clips_data = viral_analyzer_service.analyze_transcript(
                transcript_text=transcript_result["full_text"],
                words=transcript_result.get("words", []),
                video_duration=video.duration_seconds or 60.0,
                target_clip_count=5,
            )

            # 4. Generate Clips & Default Caption Models
            self._update_job(db, job, JobStage.RANKING_CLIPS, 75, "Generating ranked short-form clips and subtitle tracks")
            
            # Clear old generated clips for this video
            db.query(GeneratedClip).filter(GeneratedClip.video_id == video.id).delete()
            db.commit()

            for clip_item in clips_data:
                start_t = clip_item["start_time"]
                end_t = clip_item["end_time"]
                duration = round(end_t - start_t, 2)

                clip_record = GeneratedClip(
                    video_id=video.id,
                    title=clip_item["title"],
                    summary=clip_item.get("summary", ""),
                    hook_text=clip_item.get("hook_text", ""),
                    topic_tag=clip_item.get("topic_tag", "Growth"),
                    start_time=start_t,
                    end_time=end_t,
                    duration_seconds=duration,
                    engagement_score=clip_item.get("engagement_score", 90.0),
                    score_breakdown=clip_item.get("score_breakdown", {}),
                    aspect_ratio="9:16",
                    status=ClipStatus.READY.value,
                )
                db.add(clip_record)
                db.commit()
                db.refresh(clip_record)

                # Attach default caption styling
                caption_record = ClipCaption(
                    clip_id=clip_record.id,
                    preset_name="hormozi_yellow",
                    font_family="Arial Black",
                    font_size=42,
                    primary_color="#FFFFFF",
                    highlight_color="#FACC15",
                    stroke_color="#000000",
                    stroke_width=4,
                    position="bottom",
                    custom_words_json=[],
                )
                db.add(caption_record)
                db.commit()

                # Generate clip thumbnail
                clip_thumb_key = f"thumbnails/clips/{clip_record.id}.jpg"
                clip_thumb_path = self.storage.get_file_path_or_url(clip_thumb_key)
                if ffmpeg_service.extract_thumbnail(local_video_path, clip_thumb_path, timestamp_sec=start_t + 1.0):
                    clip_record.thumbnail_key = clip_thumb_key
                    db.commit()

            # 5. Complete pipeline
            self._update_job(db, job, JobStage.COMPLETED, 100, "All viral clips ready for studio editing and export")
            video.status = VideoStatus.COMPLETED.value
            db.commit()

            logger.info("Pipeline completed successfully for video", video_id=video.id, total_clips=len(clips_data))
            return True

        except Exception as e:
            err_msg = str(e)
            logger.error("Pipeline failed with exception", video_id=video_id, error=err_msg, trace=traceback.format_exc())
            video.status = VideoStatus.FAILED.value
            self._update_job(
                db,
                job,
                JobStage.FAILED,
                job.progress_percent,
                f"Failed: {err_msg[:100]}",
                error_code="PIPELINE_ERROR",
                error_message=err_msg,
            )
            db.commit()
            return False

    def _update_job(
        self,
        db: Session,
        job: ProcessingJob,
        stage: JobStage,
        progress: int,
        description: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        job.stage = stage.value
        job.progress_percent = progress
        job.stage_description = description
        if error_code:
            job.error_code = error_code
        if error_message:
            job.error_message = error_message
        job.updated_at = datetime.now(timezone.utc)
        db.commit()


pipeline_orchestrator = PipelineOrchestrator()
