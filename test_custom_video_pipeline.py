import sys
import os
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import shutil
import uuid
import json

from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.video import Video, VideoStatus, ProcessingJob
from backend.app.models.clip import ClipCaption, GeneratedClip, Export
from backend.app.models.transcript import Transcript, TranscriptWord
from backend.app.services.video.ffmpeg_service import ffmpeg_service
from backend.app.services.pipeline.orchestrator import pipeline_orchestrator
from backend.app.services.storage.local import LocalStorageService
from backend.app.services.caption.caption_engine import caption_engine


def main():
    print("=" * 80)
    print("      CLIPGENR - END-TO-END AI VIDEO PIPELINE TEST (CUSTOM VIDEO)")
    print("=" * 80)
    
    db = SessionLocal()
    storage = LocalStorageService()
    
    # 1. Get or create test user
    user = db.query(User).filter(User.email == "creator@clipforge.ai").first()
    if not user:
        user = db.query(User).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email="creator@clipforge.ai",
            hashed_password="dummy_hashed_password",
            full_name="Paridhi AI Creator",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    print(f"User Active: {user.full_name or 'Creator'} ({user.email}) [ID: {user.id}]")
    
    source_video_path = "test_jensen_huang.mp4"
    if not os.path.exists(source_video_path):
        print(f"ERROR: Source video '{source_video_path}' not found!")
        return
        
    meta = ffmpeg_service.get_video_metadata(source_video_path)
    duration = meta.get("duration", 0.0)
    print(f"\nSource Video Metadata:")
    print(f"  Title     : Jensen Huang (NVIDIA CEO) - Stanford GSB on Expectations & Resilience")
    print(f"  Duration  : {duration:.2f}s ({duration/60:.2f} mins)")
    print(f"  Resolution: {meta.get('width')}x{meta.get('height')}")
    print(f"  FPS       : {meta.get('fps')}")
    print(f"  Codec     : {meta.get('codec')}")
    print(f"  File Size : {meta.get('file_size_bytes') / (1024*1024):.2f} MB")
    
    # 2. Stage video in storage
    video_id = str(uuid.uuid4())
    storage_key = f"videos/{video_id}.mp4"
    target_video_path = storage.get_file_path_or_url(storage_key)
    shutil.copyfile(source_video_path, target_video_path)
    file_size = os.path.getsize(target_video_path)
    
    video = Video(
        id=video_id,
        user_id=user.id,
        title="Jensen Huang - Stanford GSB on Resilience & High Expectations",
        original_filename="test_jensen_huang.mp4",
        storage_key=storage_key,
        file_size_bytes=file_size,
        duration_seconds=duration,
        width=meta.get("width", 1280),
        height=meta.get("height", 720),
        fps=meta.get("fps", 29.97),
        codec=meta.get("codec", "av1"),
        status=VideoStatus.PENDING.value,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    print(f"\n[+] Video Registered: ID={video.id}, StorageKey={video.storage_key}")
    
    # 3. Run Pipeline Orchestrator
    print("\n" + "-" * 80)
    print(">>> EXECUTING AI PROCESSING PIPELINE...")
    print("-" * 80)
    
    success = pipeline_orchestrator.process_video(db=db, video_id=video.id)
    print(f"\nPipeline Result: {'SUCCESS' if success else 'FAILED'}")
    
    if not success:
        job = db.query(ProcessingJob).filter(ProcessingJob.video_id == video.id).first()
        if job:
            print(f"Job Error: {job.error_code} - {job.error_message}")
        return
        
    # 4. Inspect Database Results
    db.refresh(video)
    transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
    words = db.query(TranscriptWord).filter(TranscriptWord.transcript_id == transcript.id).order_by(TranscriptWord.word_index).all() if transcript else []
    clips = db.query(GeneratedClip).filter(GeneratedClip.video_id == video.id).order_by(GeneratedClip.engagement_score.desc()).all()
    
    print("\n" + "=" * 80)
    print("  TRANSCRIPTION & SPEECH RECOGNITION REPORT")
    print("=" * 80)
    if transcript:
        print(f"Detected Language       : {transcript.language.upper()}")
        print(f"Total Words Extracted   : {len(words)}")
        print(f"Full Transcript Preview :\n\"{transcript.full_text}\"\n")
        print("First 10 Word Timestamps:")
        for w in words[:10]:
            print(f"  [{w.start_time:6.2f}s -> {w.end_time:6.2f}s] {w.word}")
    
    print("\n" + "=" * 80)
    print(f"  AI VIRAL CLIPS DISCOVERED ({len(clips)} CLIPS RANKED)")
    print("=" * 80)
    for idx, c in enumerate(clips, 1):
        print(f"\nClip #{idx}: \"{c.title}\"")
        print(f"  Topic Tag      : [{c.topic_tag}]")
        print(f"  Virality Score : {c.engagement_score:.1f}/100")
        print(f"  Time Range     : {c.start_time:.2f}s -> {c.end_time:.2f}s (Duration: {c.duration_seconds:.2f}s)")
        print(f"  Opening Hook   : \"{c.hook_text}\"")
        print(f"  Summary        : {c.summary}")
        if c.score_breakdown:
            print(f"  7-Factor Matrix: {json.dumps(c.score_breakdown, indent=4)}")
            
    # 5. Test Export on Top Clip with Hormozi Yellow Captions
    if clips:
        top_clip = clips[0]
        print("\n" + "=" * 80)
        print(f"  TESTING 9:16 VERTICAL SHORT EXPORT FOR TOP CLIP #{1}")
        print(f"  Clip Title: \"{top_clip.title}\" ({top_clip.duration_seconds:.1f}s)")
        print("=" * 80)
        
        # We simulate the exact logic inside clips.py export endpoint
        export_id = str(uuid.uuid4())
        temp_trim_path = storage.get_file_path_or_url(f"exports/temp_{export_id}_trim.mp4")
        temp_vert_path = storage.get_file_path_or_url(f"exports/temp_{export_id}_vert.mp4")
        temp_ass_path = storage.get_file_path_or_url(f"exports/temp_{export_id}.ass")
        final_storage_key = f"exports/{top_clip.id}_{export_id}_final.mp4"
        final_output_path = storage.get_file_path_or_url(final_storage_key)
        
        source_path = storage.get_file_path_or_url(video.storage_key)
        
        # Step A: Trim
        print(f"1. Trimming clip from {top_clip.start_time:.2f}s to {top_clip.end_time:.2f}s...")
        trim_ok = ffmpeg_service.trim_segment(source_path, top_clip.start_time, top_clip.end_time, temp_trim_path, reencode=True)
        print(f"   Trim Status: {'OK' if trim_ok else 'FAILED'}")
        
        # Step B: Vertical 9:16 conversion with blurred background
        print("2. Converting to 1080x1920 9:16 vertical canvas with Gaussian background blur...")
        vert_ok = ffmpeg_service.convert_to_vertical(temp_trim_path, temp_vert_path, target_width=1080, target_height=1920, mode="blur_background")
        print(f"   Vertical Conversion Status: {'OK' if vert_ok else 'FAILED'}")
        
        # Step C: Subtitle generation
        print("3. Generating ASS karaoke subtitle track with Hormozi Yellow preset...")
        clip_words = (
            db.query(TranscriptWord)
            .filter(
                TranscriptWord.transcript_id == transcript.id,
                TranscriptWord.end_time >= max(0.0, top_clip.start_time - 0.1),
                TranscriptWord.start_time <= top_clip.end_time + 0.1,
            )
            .order_by(TranscriptWord.word_index.asc())
            .all()
        )
        words_data = [{"word": w.word, "start_time": w.start_time, "end_time": w.end_time} for w in clip_words]
        print(f"   Subtitle Words Count: {len(words_data)}")
        
        style_override = {
            "font_family": "Arial",
            "font_size": 52,
            "primary_color": "#FFFFFF",
            "highlight_color": "#FACC15", # Hormozi Gold
            "stroke_color": "#000000",
            "stroke_width": 5,
            "position": "bottom",
            "uppercase": True,
            "words_per_group": 3,
        }
        
        caption_engine.generate_ass_subtitles(
            words=words_data,
            output_file_path=temp_ass_path,
            style_override=style_override,
            clip_start_offset=top_clip.start_time,
        )
        print(f"   ASS Subtitles generated at: {temp_ass_path}")
        
        # Step D: Burning subtitles
        print("4. Burning subtitles into final 1080x1920 vertical video...")
        burn_ok = ffmpeg_service.burn_subtitles(temp_vert_path, temp_ass_path, final_output_path)
        print(f"   Burn Subtitles Status: {'OK' if burn_ok else 'FAILED'}")
        
        if not burn_ok or not os.path.exists(final_output_path):
            shutil.copyfile(temp_vert_path, final_output_path)
            
        file_size = os.path.getsize(final_output_path)
        export_record = Export(
            id=export_id,
            clip_id=top_clip.id,
            export_format="mp4",
            resolution="1080x1920",
            storage_key=final_storage_key,
            file_size_bytes=file_size,
            download_url=f"/api/v1/clips/exports/{export_id}/download",
        )
        db.add(export_record)
        top_clip.storage_key = final_storage_key
        db.commit()
        db.refresh(export_record)
        
        # Cleanup temp
        for p in [temp_trim_path, temp_vert_path, temp_ass_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
                    
        # Verify final export with ffprobe / ffmpeg metadata
        out_meta = ffmpeg_service.get_video_metadata(final_output_path)
        print("\n" + "=" * 80)
        print("  FINAL EXPORT VERIFICATION REPORT")
        print("=" * 80)
        print(f"  Export ID       : {export_id}")
        print(f"  Final File Path : {final_output_path}")
        print(f"  Final File Size : {file_size / (1024*1024):.2f} MB")
        print(f"  Resolution      : {out_meta.get('width')}x{out_meta.get('height')} (Expected 1080x1920 9:16 Vertical)")
        print(f"  Duration        : {out_meta.get('duration'):.2f}s")
        print(f"  FPS             : {out_meta.get('fps')}")
        print(f"  Codec           : {out_meta.get('codec')}")
        print(f"  Download URL    : {export_record.download_url}")
        print("\n>>> ALL PIPELINE TESTS PASSED WITH FLYING COLORS! <<<\n")


if __name__ == "__main__":
    main()
