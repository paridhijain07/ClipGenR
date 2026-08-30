import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import imageio_ffmpeg
from backend.app.core.logging import logger


class FFmpegService:
    """High-performance FFmpeg service utilizing bundled imageio-ffmpeg binaries."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            self.ffmpeg_exe = ffmpeg_path
        else:
            try:
                self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception as e:
                logger.warning("Could not locate imageio_ffmpeg binary, falling back to 'ffmpeg'", error=str(e))
                self.ffmpeg_exe = "ffmpeg"
        
        logger.info("FFmpegService initialized", ffmpeg_exe=self.ffmpeg_exe)

    def _run_command(self, cmd: list, timeout: int = 300) -> Tuple[bool, str, str]:
        """Run FFmpeg command securely via subprocess."""
        try:
            logger.debug("Executing FFmpeg command", cmd=" ".join(cmd))
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                check=False,
            )
            success = result.returncode == 0
            if not success:
                logger.error("FFmpeg execution failed", returncode=result.returncode, stderr=result.stderr[-1000:])
            return success, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg command timed out", timeout=timeout)
            return False, "", "Command timed out"
        except Exception as e:
            logger.error("Exception during FFmpeg execution", error=str(e))
            return False, "", str(e)

    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract video metadata (duration, width, height, fps, codec, bitrate).
        Uses FFmpeg's format parser if ffprobe is not separately available.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        file_size = os.path.getsize(video_path)
        metadata: Dict[str, Any] = {
            "duration": 0.0,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "codec": "h264",
            "bitrate": 0,
            "file_size_bytes": file_size,
        }

        # Try to run ffmpeg -i to parse stream headers
        cmd = [self.ffmpeg_exe, "-hide_banner", "-i", video_path]
        _, _, stderr = self._run_command(cmd, timeout=30)

        # Parse duration from stderr (e.g. Duration: 00:01:23.45, start: 0.000000, bitrate: 2450 kb/s)
        for line in stderr.splitlines():
            line_str = line.strip()
            if "Duration:" in line_str:
                try:
                    dur_part = line_str.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = dur_part.split(":")
                    metadata["duration"] = round(float(h) * 3600 + float(m) * 60 + float(s), 2)
                except Exception:
                    pass
                if "bitrate:" in line_str:
                    try:
                        br_part = line_str.split("bitrate:")[1].split("kb/s")[0].strip()
                        metadata["bitrate"] = int(br_part) * 1000
                    except Exception:
                        pass

            if "Stream #" in line_str and "Video:" in line_str:
                try:
                    if "h264" in line_str.lower():
                        metadata["codec"] = "h264"
                    elif "hevc" in line_str.lower() or "h265" in line_str.lower():
                        metadata["codec"] = "hevc"
                    elif "vp9" in line_str.lower():
                        metadata["codec"] = "vp9"
                    elif "av1" in line_str.lower():
                        metadata["codec"] = "av1"

                    # Find resolution like 1920x1080
                    for token in line_str.replace(",", " ").split():
                        if "x" in token and all(p.isdigit() for p in token.split("x", 1)):
                            w, h = token.split("x", 1)
                            metadata["width"] = int(w)
                            metadata["height"] = int(h)
                            break

                    # Find fps like 29.97 fps or 30 fps or 60 fps
                    if "fps" in line_str:
                        fps_tokens = line_str.split("fps")[0].strip().split()
                        if fps_tokens:
                            fps_val = float(fps_tokens[-1].replace(",", ""))
                            metadata["fps"] = round(fps_val, 2)
                except Exception:
                    pass

        return metadata

    def extract_audio(self, video_path: str, output_audio_path: str) -> bool:
        """
        Extract 16kHz mono WAV audio optimized for Whisper speech-to-text.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vn",                  # No video
            "-acodec", "pcm_s16le",  # Uncompressed 16-bit PCM WAV
            "-ar", "16000",         # 16 kHz sample rate (optimal for Whisper)
            "-ac", "1",             # Mono audio
            output_audio_path,
        ]
        success, _, _ = self._run_command(cmd, timeout=300)
        return success and os.path.exists(output_audio_path)

    def extract_thumbnail(self, video_path: str, output_image_path: str, timestamp_sec: float = 1.0) -> bool:
        """
        Extract a single high-quality frame as JPEG thumbnail.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_image_path)), exist_ok=True)
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-ss", str(max(0.0, timestamp_sec)),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",            # High JPEG quality
            output_image_path,
        ]
        success, _, _ = self._run_command(cmd, timeout=30)
        return success and os.path.exists(output_image_path)

    def trim_segment(
        self,
        video_path: str,
        start_sec: float,
        end_sec: float,
        output_path: str,
        reencode: bool = True,
    ) -> bool:
        """
        Extract a precise video segment between start_sec and end_sec.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        duration = max(0.1, end_sec - start_sec)
        
        if reencode:
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-ss", str(start_sec),
                "-i", video_path,
                "-t", str(duration),
                "-c", "copy",
                "-movflags", "+faststart",
                output_path,
            ]

        success, _, _ = self._run_command(cmd, timeout=300)
        return success and os.path.exists(output_path)

    def convert_to_vertical(
        self,
        input_video_path: str,
        output_video_path: str,
        target_width: int = 1080,
        target_height: int = 1920,
        mode: str = "blur_background",
    ) -> bool:
        """
        Convert landscape (16:9) or arbitrary video into 9:16 vertical video.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

        if mode == "crop_center":
            filter_complex = f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale={target_width}:{target_height}"
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i", input_video_path,
                "-vf", filter_complex,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                output_video_path,
            ]
        else:
            filter_complex = (
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
                f"crop={target_width}:{target_height},"
                f"boxblur=25:5[bg];"
                f"[0:v]scale={target_width}:-2[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
            )
            cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i", input_video_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                output_video_path,
            ]

        success, _, _ = self._run_command(cmd, timeout=300)
        return success and os.path.exists(output_video_path)

    def burn_subtitles(
        self,
        video_path: str,
        ass_subtitles_path: str,
        output_path: str,
    ) -> bool:
        """
        Burn styled ASS (Advanced SubStation Alpha) subtitles directly into the video stream.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        clean_ass_path = str(Path(ass_subtitles_path).resolve()).replace("\\", "/").replace(":", "\\:")
        
        cmd = [
            self.ffmpeg_exe,
            "-y",
            "-i", video_path,
            "-vf", f"ass='{clean_ass_path}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ]

        success, _, stderr = self._run_command(cmd, timeout=300)
        if not success:
            logger.warning("ASS filter failed, attempting generic subtitles filter fallback", error=stderr[-300:])
            fallback_cmd = [
                self.ffmpeg_exe,
                "-y",
                "-i", video_path,
                "-vf", f"subtitles='{clean_ass_path}'",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-c:a", "copy",
                "-movflags", "+faststart",
                output_path,
            ]
            success, _, _ = self._run_command(fallback_cmd, timeout=300)

        return success and os.path.exists(output_path)


ffmpeg_service = FFmpegService()
