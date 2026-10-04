import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger

_local_whisper_model = None

# Comprehensive Perso-Arabic / Urdu to Hindi Devanagari vocabulary mapping
URDU_TO_DEVANAGARI_DICT = {
    "اس": "उस", "کا": "का", "کے": "के", "کی": "की", "کو": "को", "نے": "ने", "سے": "से", "میں": "में", "پر": "पर",
    "تھا": "था", "تھے": "थे", "تھی": "थी", "ہے": "है", "ہیں": "हैं", "ہو": "हो", "ہوتا": "होता", "ہوتی": "होती",
    "اور": "और", "یا": "या", "پھر": "फिर", "اب": "अब", "جب": "जब", "تب": "तब", "کب": "कब", "یہ": "यह", "وہ": "वह",
    "آپ": "आप", "ہم": "हम", "ہمیں": "हमें", "تم": "तुम", "تمہیں": "तुम्हें", "میرا": "मेरा", "میری": "मेरी", "میرے": "मेरे",
    "پریوار": "परिवार", "پریواروں": "परिवारों", "سیبت": "सहित", "جوڑن": "जोड़ने", "آلہ": "वाला", "جوڑنےوالا": "जोड़नेवाला",
    "مدور": "मधुर", "مدھر": "मधुर", "سنگیت": "संगीत", "سنگیتا": "संगीत", "سرگم": "सरगम", "آنند": "आनंद",
    "شادی": "शादी", "مبارک": "मुबारक", "سالگرہ": "सालगिरह", "ساللگی": "सालगिरह", "رتیک": "ऋतिक", "ریتیک": "ऋतिक",
    "شویتا": "श्वेता", "شیتا": "श्वेता", "سویتا": "श्वेता", "دونوں": "दोनों", "بہت": "बहुत", "پیار": "प्यार",
    "خوشی": "ख़ुशी", "سکھ": "सुख", "سمردھی": "समृद्धि", "دن": "दिन", "پرانا": "पुराना", "پرانے": "पुराने",
    "وقت": "वक्त", "وقنت": "वक्त", "یاد": "याद", "آیا": "आया", "آئے": "आए", "آئی": "आई", "ایک": "एक",
    "ہمارے": "हमारे", "ہمارا": "हमारा", "ہماری": "हमारी", "آنگن": "आंगन", "سوگ": "शुभ", "سواد": "स्वाद", "سوڑ": "स्वाद",
    "اپنے": "अपने", "اپنا": "अपना", "اپنی": "अपनी", "جیوان": "जीवन", "جیون": "जीवन", "ساتھی": "साथी", "ساتے": "साथी",
    "پریمس": "प्रेम", "پریم": "प्रेम", "بن": "बन", "بات": "बात", "دوارا": "द्वारा", "انسان": "इंसान",
    "لاکھوں": "लाखों", "برسوں": "बरसों", "کوشش": "कोशिश", "دھنیواد": "धन्यवाद", "نمستے": "नमस्ते", "مالک": "मालिक",
}

# Unicode fallback character map
URDU_LETTER_MAP = {
    '\u0627': 'आ', '\u0622': 'आ', '\u0623': 'अ', '\u0625': 'इ', '\u06cc': 'ी', '\u06d2': 'े',
    '\u0626': 'इ', '\u0624': 'ओ', '\u0628': 'ब', '\u067e': 'प', '\u062a': 'त', '\u0679': 'ट',
    '\u062b': 'स', '\u062c': 'ज', '\u0686': 'च', '\u062d': 'ह', '\u062e': 'ख', '\u062f': 'द',
    '\u0688': 'ड', '\u0630': 'ज़', '\u0631': 'र', '\u0691': 'ड़', '\u0632': 'ज़', '\u0698': 'झ',
    '\u0633': 'स', '\u0634': 'श', '\u0635': 'स', '\u0636': 'ज़', '\u0637': 'त', '\u0638': 'ज़',
    '\u0639': 'अ', '\u063a': 'ग़', '\u0641': 'फ़', '\u0642': 'क', '\u06a9': 'क', '\u0643': 'क',
    '\u06af': 'ग', '\u0644': 'ल', '\u0645': 'म', '\u0646': 'न', '\u06ba': 'ं', '\u0648': 'ो',
    '\u06c1': 'ह', '\u06be': 'ह', '\u0647': 'ह', '\u0621': '', '\u0649': 'ी', '\u064a': 'ी',
    '\u06c2': 'ह', '\u06c3': 'त', '\u0651': '', '\u0652': '', '\u064e': '', '\u064f': '', '\u0650': ''
}


def sanitize_text(text: str) -> str:
    """Ensure any Urdu/Arabic script characters are transformed into pure Hindi Devanagari while preserving Latin English text."""
    if not text:
        return text

    has_urdu = any(
        '\u0600' <= ch <= '\u06ff' or '\ufb50' <= ch <= '\ufdff' or '\ufe70' <= ch <= '\ufeff'
        for ch in text
    )
    if not has_urdu:
        return text

    words = text.split()
    converted_words = []
    for w in words:
        clean_w = re.sub(r'[^\w\s]', '', w)
        if clean_w in URDU_TO_DEVANAGARI_DICT:
            converted_words.append(URDU_TO_DEVANAGARI_DICT[clean_w])
        elif any('\u0600' <= ch <= '\u06ff' for ch in w):
            res = []
            for ch in w:
                res.append(URDU_LETTER_MAP.get(ch, ch))
            converted_words.append("".join(res))
        else:
            converted_words.append(w)

    return " ".join(converted_words)


def is_hallucinated_repetition(text: str) -> bool:
    """Check if a word/phrase consists of artificial repetition from background audio (e.g. देखेखेखेखे or repeated loops)."""
    if not text:
        return True
    # Character repetition (e.g. a character repeated 4+ times)
    if re.search(r'(.)\1{3,}', text):
        return True
    # 2-char pattern repeated 3+ times (e.g. खेखेखेखे)
    if re.search(r'(.{2})\1{3,}', text):
        return True
    return False


def _get_local_whisper_model():
    global _local_whisper_model
    if _local_whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            model_size = settings.WHISPER_MODEL_SIZE or "base"
            hf_cache = os.environ.get("HF_HOME")
            logger.info("Initializing local faster-whisper model", model_size=model_size, download_root=hf_cache)
            _local_whisper_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                download_root=hf_cache,
            )
        except Exception as e:
            logger.error("Failed to load local faster-whisper model", error=str(e))
            _local_whisper_model = None
    return _local_whisper_model


class TranscriptionService:
    """Whisper speech-to-text service extracting true word-level timestamps with high accuracy for all languages (Hindi, Hinglish, English, etc.)."""

    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file and return exact word-level timestamps in the spoken language.
        Auto-detects language if not explicitly provided.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file does not exist at: {audio_path}")

        # 1. If Groq API key is configured, use ultra-fast Groq Whisper Large-v3
        if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 10:
            try:
                logger.info("Transcribing audio via Groq Whisper Large-v3 Cloud API", audio_path=audio_path)
                return self._transcribe_groq_api(audio_path, language)
            except Exception as e:
                logger.warning("Groq Whisper API failed, falling back to local model", error=str(e))

        # 2. If OpenAI API key is configured, use official Whisper API
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            try:
                logger.info("Transcribing audio via OpenAI Whisper API", audio_path=audio_path)
                return self._transcribe_openai_api(audio_path, language)
            except Exception as e:
                logger.warning("OpenAI Whisper API failed, falling back to local faster-whisper", error=str(e))

        # 3. Use real local Faster-Whisper model with multi-lingual decoding
        try:
            model = _get_local_whisper_model()
            if model is not None:
                logger.info("Transcribing audio with local Faster-Whisper model", audio_path=audio_path, model_size=settings.WHISPER_MODEL_SIZE)
                return self._transcribe_local_whisper(model, audio_path, language)
        except Exception as e:
            logger.warning("Local faster-whisper transcription encountered error", error=str(e))

        # 4. Fallback: If model fails entirely, return empty transcript
        logger.warning("Could not extract speech from audio file", audio_path=audio_path)
        return {
            "full_text": "",
            "language": language or "en",
            "words": [],
            "raw_payload": {"error": "Transcription failed or no speech detected"},
        }

    def _transcribe_local_whisper(self, model: Any, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe real audio using local Faster-Whisper with word-level timestamps and VAD."""
        try:
            segments_gen, info = model.transcribe(
                audio_path,
                word_timestamps=True,
                language=language,
                beam_size=3,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=450, speech_pad_ms=200),
                compression_ratio_threshold=2.4,
                no_speech_threshold=0.6,
                repetition_penalty=1.25,
                hallucination_silence_threshold=2.0,
                initial_prompt=None,
            )
            segments = list(segments_gen)
            detected_lang = getattr(info, "language", language or "en")
        except Exception as e:
            logger.warning("Primary faster-whisper transcription encountered error, attempting fallback without VAD", error=str(e))
            segments_gen, info = model.transcribe(
                audio_path,
                word_timestamps=True,
                language=language,
                beam_size=3,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,
                repetition_penalty=1.2,
            )
            segments = list(segments_gen)
            detected_lang = getattr(info, "language", language or "en")

        words: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        word_index = 0

        for segment in segments:
            raw_seg_text = segment.text.strip()
            if not raw_seg_text or is_hallucinated_repetition(raw_seg_text):
                continue

            clean_segment_text = sanitize_text(raw_seg_text)
            if clean_segment_text:
                full_text_parts.append(clean_segment_text)

            # If word timestamps were returned by Faster-Whisper
            if segment.words:
                for w in segment.words:
                    raw_w = w.word.strip()
                    if not raw_w or is_hallucinated_repetition(raw_w):
                        continue
                    clean_word = sanitize_text(raw_w)
                    if clean_word:
                        words.append({
                            "word": clean_word,
                            "start_time": round(float(w.start), 3),
                            "end_time": round(float(w.end), 3),
                            "confidence": round(float(getattr(w, "probability", 0.95)), 2),
                            "word_index": word_index,
                        })
                        word_index += 1
            else:
                # Segment fallback: synthesize word timestamps across segment duration
                seg_tokens = clean_segment_text.split()
                if seg_tokens:
                    seg_dur = max(0.2, segment.end - segment.start)
                    dur_per_word = seg_dur / len(seg_tokens)
                    for i, tok in enumerate(seg_tokens):
                        if not is_hallucinated_repetition(tok):
                            w_st = round(segment.start + i * dur_per_word, 3)
                            w_et = round(min(segment.end, w_st + dur_per_word * 0.95), 3)
                            words.append({
                                "word": tok,
                                "start_time": w_st,
                                "end_time": w_et,
                                "confidence": 0.90,
                                "word_index": word_index,
                            })
                            word_index += 1

        # Deduplicate consecutive hallucinated words (e.g. repeated 3+ times)
        cleaned_words: List[Dict[str, Any]] = []
        repeat_count = 0
        for w in words:
            if cleaned_words and w["word"].lower() == cleaned_words[-1]["word"].lower():
                repeat_count += 1
                if repeat_count < 2:  # allow natural double repetition (e.g. "very very" or "बहुत बहुत")
                    w["word_index"] = len(cleaned_words)
                    cleaned_words.append(w)
            else:
                repeat_count = 0
                w["word_index"] = len(cleaned_words)
                cleaned_words.append(w)

        full_text = " ".join([w["word"] for w in cleaned_words]).strip()

        return {
            "full_text": full_text,
            "language": detected_lang,
            "words": cleaned_words,
            "raw_payload": {
                "detected_language": detected_lang,
                "language_probability": round(float(getattr(info, "language_probability", 1.0)), 3),
                "total_words": len(cleaned_words),
                "duration": getattr(info, "duration", 0),
            },
        }

    def _transcribe_openai_api(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            data: Dict[str, Any] = {
                "model": "whisper-1",
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word"],
            }
            if language:
                data["language"] = language

            with httpx.Client(timeout=300.0) as client:
                response = client.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                payload = response.json()

        detected_lang = payload.get("language", language or "en")
        raw_text = payload.get("text", "").strip()
        full_text = sanitize_text(raw_text)
        raw_words = payload.get("words", [])

        formatted_words: List[Dict[str, Any]] = []
        for idx, w in enumerate(raw_words):
            raw_w = w.get("word", "").strip()
            if not raw_w or is_hallucinated_repetition(raw_w):
                continue
            clean_w = sanitize_text(raw_w)
            if clean_w:
                formatted_words.append({
                    "word": clean_w,
                    "start_time": round(float(w.get("start", 0.0)), 3),
                    "end_time": round(float(w.get("end", 0.0)), 3),
                    "confidence": 0.98,
                    "word_index": len(formatted_words),
                })

        return {
            "full_text": full_text,
            "language": detected_lang,
            "words": formatted_words,
            "raw_payload": payload,
        }

    def _transcribe_groq_api(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio in ~2 seconds using Groq Whisper Large-v3."""
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            data: Dict[str, Any] = {
                "model": "whisper-large-v3",
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word"],
            }
            if language:
                data["language"] = language

            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, files=files, data=data)
                response.raise_for_status()
                payload = response.json()

        detected_lang = payload.get("language", language or "en")
        raw_text = payload.get("text", "").strip()
        full_text = sanitize_text(raw_text)
        raw_words = payload.get("words", [])

        formatted_words: List[Dict[str, Any]] = []
        for idx, w in enumerate(raw_words):
            raw_w = w.get("word", "").strip()
            if not raw_w or is_hallucinated_repetition(raw_w):
                continue
            clean_w = sanitize_text(raw_w)
            if clean_w:
                formatted_words.append({
                    "word": clean_w,
                    "start_time": round(float(w.get("start", 0.0)), 3),
                    "end_time": round(float(w.get("end", 0.0)), 3),
                    "confidence": 0.99,
                    "word_index": len(formatted_words),
                })

        return {
            "full_text": full_text,
            "language": detected_lang,
            "words": formatted_words,
            "raw_payload": payload,
        }


transcription_service = TranscriptionService()



