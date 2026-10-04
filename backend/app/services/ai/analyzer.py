import json
import re
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger


VIRAL_ANALYSIS_SYSTEM_PROMPT = """You are an elite AI Short-Form Content Strategist specializing in identifying high-converting, viral clips from long-form videos for TikTok, YouTube Shorts, and Instagram Reels.

Analyze the provided timestamped transcript and identify the TOP 3 to 6 best viral clip candidates.
IMPORTANT: Each clip MUST start and end cleanly on full sentence boundaries.

For each clip candidate, evaluate against the 7-Factor Virality Scoring Matrix (scores 0-100):
1. hook_strength: Impact and scroll-stopping potential of the opening 3 seconds.
2. emotional_resonance: Energy spikes, conviction, humor, love, or value delivery.
3. info_density: High signal-to-noise ratio; actionable wisdom, celebration, or shocking insights.
4. standalone_coherence: Fully understandable story or insight without prior context.
5. shareability: Relatability and urge to share with peers.
6. curiosity_gap: Retention loop and satisfaction at payoff.
7. optimal_duration: 25 to 55 seconds target range.

Output ONLY valid JSON adhering strictly to this schema:
{
  "clips": [
    {
      "title": "Punchy 4-7 word viral title",
      "summary": "1-2 sentence core message",
      "hook_text": "Exact opening hook sentence",
      "topic_tag": "Celebration / Growth / Story / Mindset / Wisdom / Love",
      "start_time": 0.0,
      "end_time": 35.0,
      "engagement_score": 94.5,
      "score_breakdown": {
        "hook_strength": 96,
        "emotional_resonance": 92,
        "info_density": 95,
        "standalone_coherence": 98,
        "shareability": 91,
        "curiosity_gap": 94,
        "optimal_duration": 96
      }
    }
  ]
}
"""

HOOK_KEYWORDS = {
    "why", "how", "secret", "never", "always", "remember", "life", "wedding", "love", "family",
    "special", "shadi", "pyaar", "zindagi", "story", "growth", "money", "mistake", "best", "worst",
    "salgirah", "anniversary", "khushi", "pari", "sapna", "duniya", "dil", "sukha", "samay", "wakt",
    "truth", "stop", "look", "listen", "watch", "beautiful", "blessing", "milestone", "journey"
}


class ViralAnalyzerService:
    """AI engine that performs 7-factor viral clip discovery, scoring, and hook extraction."""

    def analyze_transcript(
        self,
        transcript_text: str,
        words: List[Dict[str, Any]],
        video_duration: float,
        target_clip_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Extract top ranked viral clips from transcript using LLMs or smart semantic sentence chunking fallback.
        """
        # 1. Try Google Gemini if configured
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10:
            try:
                logger.info("Analyzing transcript using Google Gemini AI")
                clips = self._analyze_with_gemini(transcript_text, words, video_duration)
                if clips:
                    return self._validate_and_refine_clips(clips, words, video_duration)
            except Exception as e:
                logger.warning("Gemini analysis failed, falling back to next provider", error=str(e))

        # 2. Try OpenAI GPT-4o if configured
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                logger.info("Analyzing transcript using OpenAI GPT-4o")
                clips = self._analyze_with_openai(transcript_text, words, video_duration)
                if clips:
                    return self._validate_and_refine_clips(clips, words, video_duration)
            except Exception as e:
                logger.warning("OpenAI analysis failed, falling back to heuristic engine", error=str(e))

        # 3. Smart semantic sentence-boundary chunking fallback
        logger.info("Running smart semantic sentence-boundary viral analyzer")
        return self._analyze_with_heuristics(transcript_text, words, video_duration, target_clip_count)

    def _build_timestamped_transcript_lines(self, words: List[Dict[str, Any]]) -> str:
        """Group words into timestamped sentence blocks for LLM context."""
        if not words:
            return ""

        sentences = self._group_words_into_sentences(words)
        lines = []
        for s in sentences:
            lines.append(f"[{s['start_time']:.2f}s - {s['end_time']:.2f}s]: {s['text']}")
        return "\n".join(lines)

    def _analyze_with_gemini(
        self, transcript_text: str, words: List[Dict[str, Any]], video_duration: float
    ) -> Optional[List[Dict[str, Any]]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        timestamped_script = self._build_timestamped_transcript_lines(words)
        user_content = f"Video Total Duration: {video_duration:.1f}s\n\nFull Timestamped Transcript:\n{timestamped_script}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": VIRAL_ANALYSIS_SYSTEM_PROMPT + "\n\n" + user_content}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
        }

        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return parsed.get("clips", [])

    def _analyze_with_openai(
        self, transcript_text: str, words: List[Dict[str, Any]], video_duration: float
    ) -> Optional[List[Dict[str, Any]]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        timestamped_script = self._build_timestamped_transcript_lines(words)
        user_content = f"Video Total Duration: {video_duration:.1f}s\n\nFull Timestamped Transcript:\n{timestamped_script}"

        payload = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": VIRAL_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
        }

        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("clips", [])

    def _group_words_into_sentences(self, words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group consecutive words into natural sentences based on speech pauses and punctuation."""
        if not words:
            return []

        sentences: List[Dict[str, Any]] = []
        cur_words: List[Dict[str, Any]] = []

        for i, w in enumerate(words):
            cur_words.append(w)
            is_last = (i == len(words) - 1)
            
            # Check pause to next word
            pause = 0.0
            if not is_last:
                pause = max(0.0, words[i + 1]["start_time"] - w["end_time"])

            word_str = w["word"].strip()
            ends_with_punct = any(word_str.endswith(p) for p in [".", "!", "?", "।", "\n", ";", ":"])
            is_sentence_break = ends_with_punct or (pause >= 0.45) or (len(cur_words) >= 15) or is_last

            if is_sentence_break and cur_words:
                s_text = " ".join([cw["word"] for cw in cur_words]).strip()
                sentences.append({
                    "text": s_text,
                    "start_time": round(cur_words[0]["start_time"], 3),
                    "end_time": round(cur_words[-1]["end_time"], 3),
                    "words": cur_words,
                })
                cur_words = []

        return sentences

    def _analyze_with_heuristics(
        self,
        transcript_text: str,
        words: List[Dict[str, Any]],
        video_duration: float,
        target_count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Smart semantic sentence-boundary chunker that generates strictly distinct,
        non-overlapping 22s-48s clips covering diverse highlights across the timeline.
        """
        max_dur = max(video_duration, words[-1]["end_time"] if words else 30.0)
        sentences = self._group_words_into_sentences(words)

        # Determine reasonable target clip count based on video duration
        # e.g., a 100s video can cleanly yield 3 distinct 30s clips without duplicate repetition
        clean_target = max(1, min(target_count, int(max_dur / 22.0)))

        if not sentences:
            topics = ["Growth", "Mindset", "Tactics", "Mastery", "Story"]
            clip_dur = min(35.0, max_dur / max(1, clean_target))
            clips = []
            for i in range(clean_target):
                st = round(i * (max_dur / clean_target), 2)
                et = round(min(max_dur, st + clip_dur), 2)
                clips.append({
                    "title": f"Viral Highlight: Part {i+1}",
                    "summary": f"Video highlight from {st:.1f}s to {et:.1f}s",
                    "hook_text": "Watch until the end to see this moment...",
                    "topic_tag": topics[i % len(topics)],
                    "start_time": st,
                    "end_time": et,
                    "engagement_score": round(94.0 - i * 1.5, 1),
                    "score_breakdown": {
                        "hook_strength": 95, "emotional_resonance": 92, "info_density": 90,
                        "standalone_coherence": 94, "shareability": 93, "curiosity_gap": 94, "optimal_duration": 96
                    }
                })
            return clips

        # Generate candidate multi-sentence windows
        candidates: List[Dict[str, Any]] = []
        num_sentences = len(sentences)

        for start_idx in range(num_sentences):
            accum_words: List[Dict[str, Any]] = []
            accum_text_parts: List[str] = []

            for end_idx in range(start_idx, num_sentences):
                s = sentences[end_idx]
                accum_words.extend(s["words"])
                accum_text_parts.append(s["text"])

                c_start = sentences[start_idx]["start_time"]
                c_end = sentences[end_idx]["end_time"]
                dur = c_end - c_start

                # Target short-form duration: 22s - 48s
                if 20.0 <= dur <= 48.0:
                    first_sent = sentences[start_idx]["text"]
                    all_text = " ".join(accum_text_parts)

                    # 1. Hook Score
                    hook_score = 86
                    lower_hook = first_sent.lower()
                    matched_hooks = sum(1 for kw in HOOK_KEYWORDS if kw in lower_hook)
                    hook_score = min(99, hook_score + matched_hooks * 3)
                    if any(first_sent.endswith(q) for q in ["?", "!", "।"]):
                        hook_score = min(99, hook_score + 2)

                    # 2. Optimal Duration Score (25-38s is sweet spot)
                    if 24.0 <= dur <= 38.0:
                        dur_score = 98
                    elif 20.0 <= dur <= 45.0:
                        dur_score = 92
                    else:
                        dur_score = 85

                    # 3. Speech Flow & Pacing
                    wps = len(accum_words) / max(1.0, dur)
                    flow_score = 95 if (1.8 <= wps <= 3.8) else 86

                    # 4. Overall Engagement Score
                    emotion_score = min(98, 88 + (matched_hooks * 2))
                    info_score = min(97, 89 + min(8, len(accum_words) // 10))
                    coherence_score = 96
                    share_score = min(98, 90 + matched_hooks * 2)
                    curiosity_score = min(98, 91 + (3 if "?" in first_sent else 0))

                    weights = [0.25, 0.15, 0.15, 0.15, 0.10, 0.10, 0.10]
                    scores = [hook_score, emotion_score, info_score, coherence_score, share_score, curiosity_score, dur_score]
                    total_score = round(sum(w * s for w, s in zip(weights, scores)), 1)

                    # Generate dynamic, punchy title based on key spoken phrase
                    title_tokens = [w["word"] for w in sentences[start_idx]["words"][:6]]
                    clean_title = " ".join(title_tokens).strip(" ,.-!?।")
                    if len(clean_title) > 34:
                        clean_title = clean_title[:32] + "..."
                    if not clean_title or len(clean_title) < 4:
                        clean_title = f"Highlight: {c_start:.0f}s - {c_end:.0f}s"

                    topic = self._infer_topic_tag(all_text)

                    candidates.append({
                        "title": clean_title,
                        "summary": all_text[:140] + ("..." if len(all_text) > 140 else ""),
                        "hook_text": first_sent,
                        "topic_tag": topic,
                        "start_time": max(0.0, round(c_start - 0.1, 2)),
                        "end_time": min(max_dur, round(c_end + 0.2, 2)),
                        "engagement_score": total_score,
                        "score_breakdown": {
                            "hook_strength": hook_score,
                            "emotional_resonance": emotion_score,
                            "info_density": info_score,
                            "standalone_coherence": coherence_score,
                            "shareability": share_score,
                            "curiosity_gap": curiosity_score,
                            "optimal_duration": dur_score,
                        }
                    })

        # Sort candidates by score descending
        candidates.sort(key=lambda x: x["engagement_score"], reverse=True)

        # Strict non-overlapping greedy selection:
        # Require both low overlap AND at least 12 seconds separation between clip start times
        selected: List[Dict[str, Any]] = []
        for cand in candidates:
            c_st = cand["start_time"]
            c_et = cand["end_time"]

            is_duplicate = False
            for sel in selected:
                s_st = sel["start_time"]
                s_et = sel["end_time"]
                
                # Check start-time proximity (reject clips starting within 14s of each other)
                if abs(c_st - s_st) < 14.0:
                    is_duplicate = True
                    break

                # Check duration overlap
                overlap = max(0.0, min(c_et, s_et) - max(c_st, s_st))
                min_len = min(c_et - c_st, s_et - s_st)
                if overlap / max(1.0, min_len) > 0.20:
                    is_duplicate = True
                    break

            if not is_duplicate:
                selected.append(cand)
                if len(selected) >= clean_target:
                    break

        # If we have space for more clips across the timeline, partition remaining uncovered areas
        if len(selected) < clean_target and sentences:
            selected_intervals = [(s["start_time"], s["end_time"]) for s in selected]
            # Check uncovered segments of at least 20 seconds
            step = max_dur / max(1, clean_target)
            for i in range(clean_target):
                tentative_st = i * step
                tentative_et = min(max_dur, tentative_st + min(35.0, step))
                if tentative_et - tentative_st >= 18.0:
                    # Check if already covered
                    covered = any(
                        max(0.0, min(tentative_et, s_et) - max(tentative_st, s_st)) > 8.0
                        for s_st, s_et in selected_intervals
                    )
                    if not covered:
                        # Find closest sentence window
                        s_in_range = [s for s in sentences if tentative_st - 3.0 <= s["start_time"] <= tentative_et + 3.0]
                        if s_in_range:
                            act_st = s_in_range[0]["start_time"]
                            act_et = s_in_range[-1]["end_time"]
                            c_words = [w["word"] for s in s_in_range for w in s["words"]][:6]
                            cand_title = " ".join(c_words).strip(" ,.-!?।")
                            if len(cand_title) > 34:
                                cand_title = cand_title[:32] + "..."
                            all_t = " ".join([s["text"] for s in s_in_range])
                            selected.append({
                                "title": cand_title or f"Key Moment: {act_st:.0f}s-{act_et:.0f}s",
                                "summary": all_t[:140] + ("..." if len(all_t) > 140 else ""),
                                "hook_text": s_in_range[0]["text"],
                                "topic_tag": self._infer_topic_tag(all_t),
                                "start_time": max(0.0, round(act_st - 0.1, 2)),
                                "end_time": min(max_dur, round(act_et + 0.2, 2)),
                                "engagement_score": 90.0,
                                "score_breakdown": {
                                    "hook_strength": 90, "emotional_resonance": 90, "info_density": 92,
                                    "standalone_coherence": 94, "shareability": 90, "curiosity_gap": 90, "optimal_duration": 94
                                }
                            })
                            if len(selected) >= clean_target:
                                break

        # Re-sort chronologically by start_time
        selected.sort(key=lambda x: x["start_time"])

        # Give distinct descriptive titles if any are too similar
        seen_titles = set()
        for idx, c in enumerate(selected, 1):
            if c["title"].lower() in seen_titles or len(c["title"]) < 5:
                c["title"] = f"Part {idx}: {c['title']}"
            seen_titles.add(c["title"].lower())

        return selected

    def _infer_topic_tag(self, text: str) -> str:
        """Infer topic tag from transcript content."""
        t = text.lower()
        if any(w in t for w in ["shadi", "wedding", "salgirah", "anniversary", "mubarak", "pyaar", "love", "family", "pari"]):
            return "Celebration"
        if any(w in t for w in ["money", "business", "scale", "sales", "revenue", "dollar", "finance"]):
            return "Finance"
        if any(w in t for w in ["growth", "creator", "views", "viral", "algorithm", "marketing"]):
            return "Growth"
        if any(w in t for w in ["mindset", "discipline", "focus", "habit", "success", "life"]):
            return "Mindset"
        if any(w in t for w in ["code", "ai", "tech", "software", "system"]):
            return "Tech"
        return "Story"

    def _validate_and_refine_clips(
        self, raw_clips: List[Dict[str, Any]], words: List[Dict[str, Any]], video_duration: float
    ) -> List[Dict[str, Any]]:
        """Validate LLM output clips against real video bounds and word alignments."""
        refined: List[Dict[str, Any]] = []
        for c in raw_clips:
            st = float(c.get("start_time", 0.0))
            et = float(c.get("end_time", min(video_duration, st + 35.0)))

            if et <= st:
                continue

            # Snap to closest words within range
            words_in_range = [w for w in words if max(0.0, st - 1.0) <= w["start_time"] <= et + 1.0]
            if words_in_range:
                st = max(0.0, round(words_in_range[0]["start_time"] - 0.1, 2))
                et = min(video_duration, round(words_in_range[-1]["end_time"] + 0.2, 2))

            dur = round(et - st, 2)
            if dur < 10.0:
                continue

            c["start_time"] = st
            c["end_time"] = et
            c["duration_seconds"] = dur
            if "engagement_score" not in c:
                c["engagement_score"] = 92.0
            refined.append(c)

        return refined if refined else self._analyze_with_heuristics("", words, video_duration)


viral_analyzer_service = ViralAnalyzerService()

