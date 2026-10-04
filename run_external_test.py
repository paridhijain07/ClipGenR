import sys
import os
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import shutil
import uuid

from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.video import Video, VideoStatus
from backend.app.models.clip import Clip
from backend.app.models.transcript import Transcript
from backend.app.services.video.ffmpeg_service import FFmpegService
from backend.app.services.pipeline.orchestrator import PipelineOrchestrator
from backend.app.services.export.video_exporter import VideoExporter
from backend.app.core.config import settings

def main():
    db = SessionLocal()
    ffmpeg = FFmpegService()
    
    # 1. Get or create test user
    user = db.query(User).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email="creator@clipforge.ai",
            hashed_password="dummy",
            name="ClipForge Creator"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    source_video_path = "test_external_video.mp4"
    if not os.path.exists(source_video_path):
        print("Error: test_external_video.mp4 not found!")
        return
        
    info = ffmpeg.get_video_info(source_video_path)
    duration = info.get("duration", 0.0)
    print(f"Downloaded External Video Info: Duration={duration:.2f}s ({duration/60:.2f} mins), Width={info.get('width')}, Height={info.get('height')}, FPS={info.get('fps')}")
    
    # 2. Setup video in storage
    video_id = str(uuid.uuid4())
    filename = f"{video_id}_Steve_Jobs_Stanford_Commencement.mp4"
    user_video_dir = os.path.join(settings.VIDEOS_DIR, str(user.id))
    os.makedirs(user_video_dir, exist_ok=True)
    target_video_path = os.path.join(user_video_dir, filename)
    
    shutil.copyfile(source_video_path, target_video_path)
    file_size = os.path.getsize(target_video_path)
    
    video = Video(
        id=video_id,
        user_id=user.id,
        title="Steve Jobs - Stanford Commencement Address (15 Mins)",
        filename=filename,
        file_path=target_video_path,
        file_size=file_size,
        duration=duration,
        status=VideoStatus.UPLOADED,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    print(f"\n--- Starting Full AI Pipeline for Video: {video.title} (ID: {video.id}) ---")
    orchestrator = PipelineOrchestrator(db=db)
    
    success = orchestrator.process_video(video_id=video.id, background_tasks=None)
    print(f"\nPipeline Execution Result: {'SUCCESS' if success else 'FAILED'}")
    
    # Query results
    db.refresh(video)
    transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
    clips = db.query(Clip).filter(Clip.video_id == video.id).order_by(Clip.virality_score.desc()).all()
    
    print("\n" + "="*70)
    print("TRANSCRIPTION BENCHMARK RESULTS")
    print("="*70)
    if transcript:
        words = transcript.words or []
        print(f"Total Words Transcribed : {len(words)}")
        print(f"Detected Language       : {transcript.language}")
        print(f"Full Transcript Preview : {transcript.full_text[:500]}...\n")
    else:
        print("No transcript record found!")
        
    print("="*70)
    print(f"EXTRACTED VIRAL CLIPS ({len(clips)} Total)")
    print("="*70)
    for i, clip in enumerate(clips, 1):
        print(f"\nClip #{i} [{clip.start_time:.1f}s -> {clip.end_time:.1f}s] (Duration: {clip.duration:.1f}s)")
        print(f"  Title          : {clip.title}")
        print(f"  Topic          : {clip.topic}")
        print(f"  Virality Score : {clip.virality_score:.1f}/100")
        print(f"  Hook           : \"{clip.hook}\"")
        print(f"  Summary        : {clip.summary}")
        if clip.score_breakdown:
            print(f"  Breakdown      : {clip.score_breakdown}")
            
    # Export the #1 clip to test ASS subtitle rendering & vertical export
    if clips:
        top_clip = clips[0]
        print("\n" + "="*70)
        print(f"TESTING 1080x1920 VERTICAL SHORT VIDEO EXPORT FOR CLIP #1 ({top_clip.title})")
        print("="*70)
        exporter = VideoExporter(db=db)
        export_job = exporter.export_clip(
            clip_id=top_clip.id,
            template_id="hormozi",
            include_captions=True,
            include_audio_enhancement=False,
            export_format="mp4"
        )
        print(f"Export Job Status : {export_job.status}")
        print(f"Exported File Path: {export_job.file_path}")
        if export_job.file_path and os.path.exists(export_job.file_path):
            size_mb = os.path.getsize(export_job.file_path) / (1024 * 1024)
            print(f"Exported File Size: {size_mb:.2f} MB")
            print("Vertical Short Video Export SUCCESSFUL!")

if __name__ == "__main__":
    main()
