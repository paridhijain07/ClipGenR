import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    HAS_TRANSLITERATION = True
except ImportError:
    HAS_TRANSLITERATION = False


def devanagari_to_hinglish(text: str) -> str:
    """Convert Hindi Devanagari characters into natural, readable Romanized Hinglish."""
    if not HAS_TRANSLITERATION:
        return text
    try:
        res = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        replacements = {
            "aa": "aa", "ii": "ee", "uu": "oo",
            "shh": "sh", "Sh": "sh", "RRi": "ri", "R^i": "ri",
            "~N": "n", "~n": "n", "N^": "n",
            ".n": "n", "M": "n", "H": "h",
            "kh": "kh", "gh": "gh", "ch": "ch", "jh": "jh",
            "th": "th", "dh": "dh", "ph": "ph", "bh": "bh",
        }
        for k, v in replacements.items():
            res = res.replace(k, v)
        return res
    except Exception:
        return text


PRESET_STYLES: Dict[str, Dict[str, Any]] = {
    "hormozi_yellow": {
        "name": "Hormozi Viral (Hinglish / Hindi)",
        "description": "High-impact uppercase yellow and green karaoke highlighting on bold font",
        "font_family": "Nirmala UI",
        "font_size": 42,
        "primary_color": "#FFFFFF",      # Default text (White)
        "highlight_color": "#FACC15",    # Active word (Vibrant Gold/Yellow)
        "secondary_color": "#22C55E",    # Accent word (Electric Green)
        "stroke_color": "#000000",       # Outline (Black)
        "stroke_width": 4,
        "position": "bottom",            # top, center, bottom
        "uppercase": True,
        "words_per_group": 3,
    },
    "beast_bold": {
        "name": "Beast Pop (Hinglish)",
        "description": "Dynamic vibrant pop with bold blue outline and rapid single/double word flashes",
        "font_family": "Nirmala UI",
        "font_size": 46,
        "primary_color": "#FFFFFF",
        "highlight_color": "#38BDF8",    # Sky Blue
        "secondary_color": "#F43F5E",    # Rose Red
        "stroke_color": "#0F172A",
        "stroke_width": 5,
        "position": "center",
        "uppercase": True,
        "words_per_group": 2,
    },
    "neon_cyber": {
        "name": "Neon Cyber",
        "description": "Futuristic neon glowing aesthetic with cyan and magenta accents",
        "font_family": "Nirmala UI",
        "font_size": 40,
        "primary_color": "#F8FAFC",
        "highlight_color": "#06B6D4",    # Cyan
        "secondary_color": "#D946EF",    # Magenta
        "stroke_color": "#020617",
        "stroke_width": 3,
        "position": "bottom",
        "uppercase": False,
        "words_per_group": 4,
    },
    "minimal_clean": {
        "name": "Clean Minimalist",
        "description": "Understated, modern corporate subtitle bar with high legibility",
        "font_family": "Nirmala UI",
        "font_size": 34,
        "primary_color": "#FFFFFF",
        "highlight_color": "#E2E8F0",
        "secondary_color": "#94A3B8",
        "stroke_color": "#000000",
        "stroke_width": 2,
        "position": "bottom",
        "uppercase": False,
        "words_per_group": 5,
    },
}


def hex_to_ass_color(hex_color: str, alpha: str = "00") -> str:
    """Convert standard hex (#RRGGBB) to ASS color format (&HAABBGGRR)."""
    hex_clean = hex_color.lstrip("#")
    if len(hex_clean) == 6:
        r = hex_clean[0:2]
        g = hex_clean[2:4]
        b = hex_clean[4:6]
        return f"&H{alpha}{b}{g}{r}&"
    return "&H00FFFFFF&"


def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.CC (centiseconds)."""
    total_cs = int(max(0.0, seconds) * 100)
    cs = total_cs % 100
    total_sec = total_cs // 100
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hour = total_min // 60
    return f"{hour}:{min_:02d}:{sec:02d}.{cs:02d}"


class CaptionEngine:
    """Generates styled ASS and WebVTT subtitle files for video overlay and preview."""

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        return PRESET_STYLES.get(preset_name, PRESET_STYLES["hormozi_yellow"])

    def list_presets(self) -> List[Dict[str, Any]]:
        return [
            {"id": key, **config}
            for key, config in PRESET_STYLES.items()
        ]

    def generate_ass_subtitles(
        self,
        words: List[Dict[str, Any]],
        output_file_path: str,
        style_override: Optional[Dict[str, Any]] = None,
        clip_start_offset: float = 0.0,
    ) -> str:
        """
        Generate an Advanced SubStation Alpha (.ass) subtitle file with word-by-word active karaoke highlights.
        Supports Hindi Devanagari and Romanized Hinglish formatting.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)

        preset = style_override or self.get_preset("hormozi_yellow")
        font_name = preset.get("font_family", "Nirmala UI")
        font_size = preset.get("font_size", 42)
        primary_color_ass = hex_to_ass_color(preset.get("primary_color", "#FFFFFF"))
        highlight_color_ass = hex_to_ass_color(preset.get("highlight_color", "#FACC15"))
        outline_color_ass = hex_to_ass_color(preset.get("stroke_color", "#000000"))
        outline_width = preset.get("stroke_width", 4)
        uppercase = preset.get("uppercase", True)
        words_per_group = preset.get("words_per_group", 3)
        position = preset.get("position", "bottom")
        use_hinglish = preset.get("use_hinglish", False)

        alignment = 2
        margin_v = 180
        if position == "center":
            alignment = 5
            margin_v = 0
        elif position == "top":
            alignment = 8
            margin_v = 220

        ass_header = f"""[Script Info]
Title: ClipGenR AI Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color_ass},&H000000FF&,{outline_color_ass},&H80000000&,-1,0,0,0,100,100,1,0,1,{outline_width},0,{alignment},50,50,{margin_v},1
Style: Highlight,{font_name},{font_size},{highlight_color_ass},&H000000FF&,{outline_color_ass},&H80000000&,-1,0,0,0,100,100,1,0,1,{outline_width},0,{alignment},50,50,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events: List[str] = []

        if not words:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(ass_header)
            return output_file_path

        chunks: List[List[Dict[str, Any]]] = []
        for i in range(0, len(words), words_per_group):
            chunks.append(words[i : i + words_per_group])

        for chunk in chunks:
            if not chunk:
                continue

            for active_idx, active_word in enumerate(chunk):
                w_start = max(0.0, active_word["start_time"] - clip_start_offset)
                w_end = max(w_start + 0.15, active_word["end_time"] - clip_start_offset)

                start_str = format_ass_time(w_start)
                end_str = format_ass_time(w_end)

                text_parts = []
                for idx, w in enumerate(chunk):
                    raw_text = w["word"].strip()
                    if use_hinglish:
                        raw_text = devanagari_to_hinglish(raw_text)

                    if uppercase:
                        raw_text = raw_text.upper()

                    if idx == active_idx:
                        text_parts.append(f"{{\\c{highlight_color_ass}\\fscx108\\fscy108}}{raw_text}{{\\rDefault}}")
                    else:
                        text_parts.append(raw_text)

                line_text = " ".join(text_parts)
                events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(events) + "\n")

        logger.info("Generated ASS subtitles", path=output_file_path, total_events=len(events))
        return output_file_path


caption_engine = CaptionEngine()
