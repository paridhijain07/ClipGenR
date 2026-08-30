import os
import pytest
from backend.app.core.config import settings
from backend.app.models.clip import ClipCaption, GeneratedClip
from backend.app.models.video import JobStage, Video, VideoStatus
from backend.app.schemas.clip import ClipCaptionRead, GeneratedClipRead
from backend.app.services.ai.analyzer import viral_analyzer_service
from backend.app.services.caption.caption_engine import (
    caption_engine,
    format_ass_time,
    hex_to_ass_color,
)
from backend.app.services.storage.local import LocalStorageService


def test_config_defaults():
    assert settings.PROJECT_NAME == "ClipGenR AI"
    assert settings.API_V1_STR == "/api/v1"
    assert ".mp4" in settings.ALLOWED_VIDEO_EXTENSIONS


def test_ass_color_conversion():
    # #FFFFFF -> &H00FFFFFF&
    white = hex_to_ass_color("#FFFFFF")
    assert white == "&H00FFFFFF&"
    # #FACC15 -> &H0015CCFA& (BBGGRR)
    gold = hex_to_ass_color("#FACC15")
    assert gold == "&H0015CCFA&"


def test_ass_time_formatting():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(65.42) == "0:01:05.42"
    assert format_ass_time(3661.05) == "1:01:01.05"


def test_caption_presets():
    presets = caption_engine.list_presets()
    preset_ids = [p["id"] for p in presets]
    assert "hormozi_yellow" in preset_ids
    assert "beast_bold" in preset_ids
    assert "neon_cyber" in preset_ids
    assert "minimal_clean" in preset_ids


def test_local_storage_service(tmp_path):
    storage = LocalStorageService(base_dir=str(tmp_path))
    test_key = "tests/hello.txt"
    test_bytes = b"Hello ClipGenR AI"

    saved_key = storage.save_bytes(test_bytes, test_key)
    assert saved_key == test_key
    assert storage.exists(test_key) is True

    resolved_path = storage.get_file_path_or_url(test_key)
    assert os.path.exists(resolved_path)

    deleted = storage.delete_file(test_key)
    assert deleted is True
    assert storage.exists(test_key) is False


def test_viral_analyzer_heuristic_scoring():
    sample_words = [
        {"word": "Here", "start_time": 0.0, "end_time": 0.3},
        {"word": "is", "start_time": 0.3, "end_time": 0.5},
        {"word": "the", "start_time": 0.5, "end_time": 0.7},
        {"word": "secret", "start_time": 0.7, "end_time": 1.2},
        {"word": "to", "start_time": 1.2, "end_time": 1.4},
        {"word": "going", "start_time": 1.4, "end_time": 1.8},
        {"word": "viral", "start_time": 1.8, "end_time": 2.4},
    ]
    # Add dummy words to simulate a 90 second video
    for i in range(100):
        sample_words.append({
            "word": f"word{i}",
            "start_time": 2.5 + i * 0.8,
            "end_time": 3.2 + i * 0.8,
        })

    clips = viral_analyzer_service.analyze_transcript(
        transcript_text="Here is the secret to going viral...",
        words=sample_words,
        video_duration=85.0,
        target_clip_count=3,
    )

    assert len(clips) >= 1
    top_clip = clips[0]
    assert top_clip["engagement_score"] >= 80.0
    assert "hook_strength" in top_clip["score_breakdown"]
    assert "emotional_resonance" in top_clip["score_breakdown"]
    assert "info_density" in top_clip["score_breakdown"]
    assert "standalone_coherence" in top_clip["score_breakdown"]
    assert "shareability" in top_clip["score_breakdown"]
    assert "curiosity_gap" in top_clip["score_breakdown"]
    assert "optimal_duration" in top_clip["score_breakdown"]


def test_ass_subtitle_generation(tmp_path):
    output_ass = str(tmp_path / "test_subs.ass")
    sample_words = [
        {"word": "STOP", "start_time": 0.0, "end_time": 0.5},
        {"word": "SCROLLING", "start_time": 0.5, "end_time": 1.2},
        {"word": "NOW", "start_time": 1.2, "end_time": 1.8},
    ]

    path = caption_engine.generate_ass_subtitles(
        words=sample_words,
        output_file_path=output_ass,
        clip_start_offset=0.0,
    )

    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "[Script Info]" in content
    assert "Style: Default" in content
    assert "Dialogue:" in content
    assert "STOP" in content
    assert "SCROLLING" in content
