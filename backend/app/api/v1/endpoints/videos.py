import os
import uuid
from typing import Any, List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    get_current_active_user,
    get_db,
    get_storage_service,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.clip import GeneratedClip
from backend.app.models.user import User
from backend.app.models.video import JobStage, ProcessingJob, Video, VideoStatus
from backend.app.schemas.common import APIResponse
from backend.app.schemas.video import (
    ProcessingJobRead,
    VideoDetailRead,
    VideoRead,
)
from backend.app.services.storage.base import BaseStorageService
from backend.app.worker import run_pipeline_task

router = APIRouter()


@router.post("/upload", response_model=VideoRead)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    auto_process: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage: BaseStorageService = Depends(get_storage_service),
) -> Any:
    """
    Direct multipart video upload. Stores original file and queues AI processing.
    """
    import re
    raw_filename = file.filename or "uploaded_video.mp4"
    clean_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', raw_filename)
    ext = os.path.splitext(clean_filename)[1].lower()

    if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)}",
        )

    # Generate unique storage key
    video_id = str(uuid.uuid4())
    storage_key = f"videos/{current_user.id}/{video_id}_{clean_filename}"

    try:
        # Save file to storage
        storage.save_file(file.file, storage_key, content_type=file.content_type)
    except Exception as e:
        logger.error("Failed to persist uploaded video", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write uploaded file: {str(e)}",
        )

    # Get local file size
    local_path = storage.get_file_path_or_url(storage_key)
    file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0

    video_title = title or os.path.splitext(raw_filename)[0].replace("_", " ").title()

    video = Video(
        id=video_id,
        user_id=current_user.id,
        title=video_title,
        original_filename=raw_filename,
        storage_key=storage_key,
        file_size_bytes=file_size,
        status=VideoStatus.PENDING.value,
    )
    db.add(video)
    db.commit()

    # Create processing job
    job = ProcessingJob(
        video_id=video.id,
        stage=JobStage.QUEUED.value,
        progress_percent=0,
        stage_description="Video uploaded, awaiting AI pipeline processing",
    )
    db.add(job)
    db.commit()
    db.refresh(video)

    if auto_process:
        logger.info("Scheduling automated video pipeline task", video_id=video.id)
        background_tasks.add_task(run_pipeline_task, video_id=video.id, job_id=job.id)

    # Construct response
    video_read = VideoRead.model_validate(video)
    video_read.active_job = ProcessingJobRead.model_validate(job)
    video_read.clip_count = 0
    return video_read


@router.get("", response_model=List[VideoRead])
def list_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """List all uploaded videos belonging to the current user."""
    videos = (
        db.query(Video)
        .filter(Video.user_id == current_user.id)
        .order_by(Video.created_at.desc())
        .all()
    )

    results: List[VideoRead] = []
    for v in videos:
        vr = VideoRead.model_validate(v)
        # Fetch clip count
        vr.clip_count = db.query(GeneratedClip).filter(GeneratedClip.video_id == v.id).count()
        # Fetch latest active job
        latest_job = db.query(ProcessingJob).filter(ProcessingJob.video_id == v.id).order_by(ProcessingJob.created_at.desc()).first()
        if latest_job:
            vr.active_job = ProcessingJobRead.model_validate(latest_job)
        results.append(vr)

    return results


@router.get("/{video_id}", response_model=VideoDetailRead)
def get_video_detail(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get single video details, processing jobs, and status."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    v_detail = VideoDetailRead.model_validate(video)
    v_detail.clip_count = db.query(GeneratedClip).filter(GeneratedClip.video_id == video.id).count()
    latest_job = db.query(ProcessingJob).filter(ProcessingJob.video_id == video.id).order_by(ProcessingJob.created_at.desc()).first()
    if latest_job:
        v_detail.active_job = ProcessingJobRead.model_validate(latest_job)
    return v_detail


@router.post("/{video_id}/process", response_model=ProcessingJobRead)
def trigger_video_processing(
    video_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Trigger or re-run AI processing pipeline for a video."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    job = ProcessingJob(
        video_id=video.id,
        stage=JobStage.QUEUED.value,
        progress_percent=0,
        stage_description="Queueing video for AI viral analysis",
    )
    db.add(job)
    video.status = VideoStatus.PENDING.value
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_pipeline_task, video_id=video.id, job_id=job.id)
    return ProcessingJobRead.model_validate(job)


@router.get("/{video_id}/status", response_model=ProcessingJobRead)
def get_video_processing_status(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Poll live processing job stage and progress percentage."""
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.video_id == video_id)
        .order_by(ProcessingJob.created_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processing job found for this video.",
        )
    return ProcessingJobRead.model_validate(job)


@router.delete("/{video_id}", response_model=APIResponse)
def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage: BaseStorageService = Depends(get_storage_service),
) -> Any:
    """Delete video, generated clips, transcripts, and storage files."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == current_user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found.",
        )

    # Delete files from disk
    if video.storage_key:
        storage.delete_file(video.storage_key)
    if video.audio_storage_key:
        storage.delete_file(video.audio_storage_key)
    if video.thumbnail_key:
        storage.delete_file(video.thumbnail_key)

    db.delete(video)
    db.commit()

    return APIResponse(success=True, message="Video deleted successfully.")


@router.get("/stream/{storage_key:path}")
def stream_media(
    storage_key: str,
    request: Request,
    storage: BaseStorageService = Depends(get_storage_service),
):
    """
    Stream media files (video/audio/images) with full HTTP 206 Partial Content Range support.
    """
    file_path = storage.get_file_path_or_url(storage_key)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found.",
        )

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    # Content type resolution
    content_type = "video/mp4"
    if file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif file_path.endswith(".png"):
        content_type = "image/png"
    elif file_path.endswith(".wav"):
        content_type = "audio/wav"
    elif file_path.endswith(".webm"):
        content_type = "video/webm"

    if not range_header or not content_type.startswith("video"):
        return FileResponse(file_path, media_type=content_type)

    # HTTP Byte-Range streaming for smooth video playback & seeking
    try:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = (end - start) + 1

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = chunk_size
                while bytes_left > 0:
                    read_size = min(bytes_left, 1024 * 1024)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    bytes_left -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)
    except Exception:
        return FileResponse(file_path, media_type=content_type)
