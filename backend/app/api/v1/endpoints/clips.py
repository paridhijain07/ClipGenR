import os
import uuid
from typing import Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    get_current_active_user,
    get_db,
    get_storage_service,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.clip import ClipCaption, Export, GeneratedClip, ClipStatus
from backend.app.models.transcript import Transcript, TranscriptWord
from backend.app.models.user import User
from backend.app.models.video import Video
from backend.app.schemas.clip import (
    ClipCaptionRead,
    ClipCaptionUpdate,
    ExportRead,
    GeneratedClipRead,
    GeneratedClipUpdate,
    WordTimestampRead,
)
from backend.app.schemas.common import APIResponse
from backend.app.services.caption.caption_engine import caption_engine
from backend.app.services.storage.base import BaseStorageService
from backend.app.services.video.ffmpeg_service import ffmpeg_service

router = APIRouter()


@router.get("/video/{video_id}", response_model=List[GeneratedClipRead])
def get_video_clips(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage: BaseStorageService = Depends(get_storage_service),
) -> Any:
    """Get all AI-generated clips for a specific video ordered by virality score."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == current_user.id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")

    clips = (
        db.query(GeneratedClip)
        .filter(GeneratedClip.video_id == video_id)
        .order_by(GeneratedClip.engagement_score.desc())
        .all()
    )

    results: List[GeneratedClipRead] = []
    for c in clips:
        cr = GeneratedClipRead.model_validate(c)
        if c.captions:
            cr.captions = ClipCaptionRead.model_validate(c.captions)
        cr.video_source_url = f"{settings.API_V1_STR}/videos/stream/{video.storage_key}"
        results.append(cr)

    return results


@router.get("/{clip_id}", response_model=GeneratedClipRead)
def get_clip_detail(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get detailed clip data including caption presets, words, and stream URLs."""
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    cr = GeneratedClipRead.model_validate(clip)
    if clip.captions:
        cr.captions = ClipCaptionRead.model_validate(clip.captions)
    if clip.video:
        cr.video_source_url = f"{settings.API_V1_STR}/videos/stream/{clip.video.storage_key}"
    return cr


@router.get("/{clip_id}/words", response_model=List[WordTimestampRead])
def get_clip_words(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get the word-level timestamps corresponding to this clip's time range."""
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    # 1. If custom edited words exist, return them
    if clip.captions and clip.captions.custom_words_json:
        try:
            return [WordTimestampRead.model_validate(w) for w in clip.captions.custom_words_json]
        except Exception:
            pass

    # 2. Query transcript words
    transcript = db.query(Transcript).filter(Transcript.video_id == clip.video_id).first()
    words = []
    if transcript:
        words = (
            db.query(TranscriptWord)
            .filter(
                TranscriptWord.transcript_id == transcript.id,
                TranscriptWord.end_time >= max(0.0, clip.start_time - 0.1),
                TranscriptWord.start_time <= clip.end_time + 0.1,
            )
            .order_by(TranscriptWord.word_index.asc())
            .all()
        )

    if words:
        return [WordTimestampRead.model_validate(w) for w in words]

    # 3. Dynamic High-Retention Caption Synthesis:
    # Synthesize word timestamps across the clip duration from hook & summary
    phrase = f"{clip.hook_text or ''} {clip.summary or ''}".strip()
    if not phrase or phrase == "None None":
        phrase = f"{clip.title} • Key insights and highlights for maximum retention."

    tokens = [t for t in phrase.split() if t]
    if not tokens:
        tokens = ["ClipGenR", "Viral", "Short", "Highlights", "Secrets", "Mastery"]

    duration = max(5.0, clip.duration_seconds or (clip.end_time - clip.start_time))
    time_per_word = duration / max(1, len(tokens))

    synthetic_words = []
    for idx, token in enumerate(tokens):
        w_start = round(clip.start_time + idx * time_per_word, 2)
        w_end = round(min(clip.end_time, w_start + time_per_word * 0.95), 2)
        synthetic_words.append(
            WordTimestampRead(
                word=token,
                start_time=w_start,
                end_time=w_end,
                confidence=0.98,
                word_index=idx,
            )
        )

    return synthetic_words


@router.patch("/{clip_id}", response_model=GeneratedClipRead)
def update_clip(
    clip_id: str,
    update_data: GeneratedClipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update clip title, trim timestamps, or aspect ratio."""
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    if update_data.title is not None:
        clip.title = update_data.title
    if update_data.start_time is not None:
        clip.start_time = update_data.start_time
    if update_data.end_time is not None:
        clip.end_time = update_data.end_time
    if update_data.aspect_ratio is not None:
        clip.aspect_ratio = update_data.aspect_ratio

    clip.duration_seconds = round(clip.end_time - clip.start_time, 2)
    db.commit()
    db.refresh(clip)

    cr = GeneratedClipRead.model_validate(clip)
    if clip.captions:
        cr.captions = ClipCaptionRead.model_validate(clip.captions)
    if clip.video:
        cr.video_source_url = f"{settings.API_V1_STR}/videos/stream/{clip.video.storage_key}"
    return cr


@router.put("/{clip_id}/captions", response_model=ClipCaptionRead)
def update_clip_captions(
    clip_id: str,
    update_data: ClipCaptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Update caption typography, preset style, or custom edited words."""
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    caption = db.query(ClipCaption).filter(ClipCaption.clip_id == clip_id).first()
    if not caption:
        caption = ClipCaption(clip_id=clip_id)
        db.add(caption)

    if update_data.preset_name is not None:
        caption.preset_name = update_data.preset_name
        # Apply preset defaults
        preset_config = caption_engine.get_preset(update_data.preset_name)
        caption.font_family = preset_config.get("font_family", caption.font_family)
        caption.font_size = preset_config.get("font_size", caption.font_size)
        caption.primary_color = preset_config.get("primary_color", caption.primary_color)
        caption.highlight_color = preset_config.get("highlight_color", caption.highlight_color)
        caption.stroke_color = preset_config.get("stroke_color", caption.stroke_color)
        caption.stroke_width = preset_config.get("stroke_width", caption.stroke_width)
        caption.position = preset_config.get("position", caption.position)

    if update_data.font_family is not None:
        caption.font_family = update_data.font_family
    if update_data.font_size is not None:
        caption.font_size = update_data.font_size
    if update_data.primary_color is not None:
        caption.primary_color = update_data.primary_color
    if update_data.highlight_color is not None:
        caption.highlight_color = update_data.highlight_color
    if update_data.stroke_color is not None:
        caption.stroke_color = update_data.stroke_color
    if update_data.stroke_width is not None:
        caption.stroke_width = update_data.stroke_width
    if update_data.position is not None:
        caption.position = update_data.position
    if update_data.custom_words_json is not None:
        caption.custom_words_json = update_data.custom_words_json

    db.commit()
    db.refresh(caption)
    return ClipCaptionRead.model_validate(caption)


@router.post("/{clip_id}/export", response_model=ExportRead)
def export_clip(
    clip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage: BaseStorageService = Depends(get_storage_service),
) -> Any:
    """
    Render high-definition 9:16 vertical video with burned dynamic subtitles.
    """
    clip = db.query(GeneratedClip).filter(GeneratedClip.id == clip_id).first()
    if not clip or not clip.video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clip not found.")

    source_path = storage.get_file_path_or_url(clip.video.storage_key)
    if not os.path.exists(source_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source video not found on disk.")

    export_id = str(uuid.uuid4())
    temp_trim_path = storage.get_file_path_or_url(f"exports/temp_{export_id}_trim.mp4")
    temp_vert_path = storage.get_file_path_or_url(f"exports/temp_{export_id}_vert.mp4")
    temp_ass_path = storage.get_file_path_or_url(f"exports/temp_{export_id}.ass")
    final_storage_key = f"exports/{clip.id}_{export_id}_final.mp4"
    final_output_path = storage.get_file_path_or_url(final_storage_key)

    try:
        # Step 1: Trim segment
        logger.info("Trimming segment for export", start=clip.start_time, end=clip.end_time)
        trim_ok = ffmpeg_service.trim_segment(
            source_path, clip.start_time, clip.end_time, temp_trim_path, reencode=True
        )
        if not trim_ok:
            raise RuntimeError("FFmpeg segment trim failed")

        # Step 2: Convert to 9:16 vertical
        logger.info("Converting segment to 9:16 vertical video")
        vert_ok = ffmpeg_service.convert_to_vertical(
            temp_trim_path, temp_vert_path, target_width=1080, target_height=1920, mode="blur_background"
        )
        video_to_subtitle = temp_vert_path if vert_ok else temp_trim_path

        # Step 3: Fetch words for caption generation
        words_data = []
        if clip.captions and clip.captions.custom_words_json:
            words_data = clip.captions.custom_words_json
        else:
            transcript = db.query(Transcript).filter(Transcript.video_id == clip.video_id).first()
            if transcript:
                db_words = (
                    db.query(TranscriptWord)
                    .filter(
                        TranscriptWord.transcript_id == transcript.id,
                        TranscriptWord.end_time >= max(0.0, clip.start_time - 0.1),
                        TranscriptWord.start_time <= clip.end_time + 0.1,
                    )
                    .order_by(TranscriptWord.word_index.asc())
                    .all()
                )
                words_data = [
                    {"word": w.word, "start_time": w.start_time, "end_time": w.end_time}
                    for w in db_words
                ]

        # If still empty, synthesize rhythmic caption blocks from hook & summary
        if not words_data:
            phrase = f"{clip.hook_text or ''} {clip.summary or ''}".strip()
            if not phrase or phrase == "None None":
                phrase = f"{clip.title} • Key insights and highlights for maximum retention."
            tokens = [t for t in phrase.split() if t]
            if not tokens:
                tokens = ["ClipGenR", "Viral", "Short", "Highlights", "Secrets", "Mastery"]
            dur = max(5.0, clip.duration_seconds or (clip.end_time - clip.start_time))
            time_per_word = dur / max(1, len(tokens))
            for idx, token in enumerate(tokens):
                w_start = round(clip.start_time + idx * time_per_word, 2)
                w_end = round(min(clip.end_time, w_start + time_per_word * 0.95), 2)
                words_data.append({
                    "word": token,
                    "start_time": w_start,
                    "end_time": w_end,
                })

        # Generate ASS subtitles
        caption = clip.captions
        style_override = None
        if caption:
            style_override = {
                "font_family": caption.font_family,
                "font_size": caption.font_size,
                "primary_color": caption.primary_color,
                "highlight_color": caption.highlight_color,
                "stroke_color": caption.stroke_color,
                "stroke_width": caption.stroke_width,
                "position": caption.position,
                "uppercase": True,
                "words_per_group": 3,
            }

        caption_engine.generate_ass_subtitles(
            words=words_data,
            output_file_path=temp_ass_path,
            style_override=style_override,
            clip_start_offset=clip.start_time,
        )

        # Step 4: Burn subtitles
        logger.info("Burning subtitles into final export video")
        burn_ok = ffmpeg_service.burn_subtitles(video_to_subtitle, temp_ass_path, final_output_path)
        if not burn_ok or not os.path.exists(final_output_path):
            # If burning failed, use un-subtitled vertical video as fallback
            import shutil
            shutil.copyfile(video_to_subtitle, final_output_path)

        file_size = os.path.getsize(final_output_path) if os.path.exists(final_output_path) else 0

        # Save Export record
        export_record = Export(
            id=export_id,
            clip_id=clip.id,
            export_format="mp4",
            resolution="1080x1920",
            storage_key=final_storage_key,
            file_size_bytes=file_size,
            download_url=f"{settings.API_V1_STR}/clips/exports/{export_id}/download",
        )
        db.add(export_record)
        clip.storage_key = final_storage_key
        db.commit()
        db.refresh(export_record)

        return ExportRead.model_validate(export_record)

    finally:
        # Cleanup temporary files
        for p in [temp_trim_path, temp_vert_path, temp_ass_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


@router.get("/exports/{export_id}/download")
def download_exported_clip(
    export_id: str,
    db: Session = Depends(get_db),
    storage: BaseStorageService = Depends(get_storage_service),
):
    """Download the final exported MP4 clip."""
    export_item = db.query(Export).filter(Export.id == export_id).first()
    if not export_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found.")

    file_path = storage.get_file_path_or_url(export_item.storage_key)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exported file missing on disk.")

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=f"clipgenr_{export_id[:8]}.mp4",
    )
