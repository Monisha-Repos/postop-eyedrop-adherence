"""Gemini text-to-speech. Returns WAV bytes, or None so the iPad falls back to its on-device voice."""
import hashlib
import io
import logging
import wave

from . import config

log = logging.getLogger(__name__)

# Small in-memory cache: the same script is often played more than once.
_cache: dict[str, bytes] = {}
_CACHE_MAX = 200


def _pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    """Gemini TTS returns raw 16-bit mono PCM at 24 kHz; wrap it so AVAudioPlayer can play it."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def synthesize(script: str) -> bytes | None:
    if not config.GEMINI_API_KEY:
        return None
    key = hashlib.sha256(script.encode()).hexdigest()
    if key in _cache:
        return _cache[key]
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=config.GEMINI_TTS_MODEL,
            contents=f"Say this slowly, warmly and clearly, like a kind grandparent: {script}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=config.GEMINI_TTS_VOICE)
                    )
                ),
            ),
        )
        pcm = response.candidates[0].content.parts[0].inline_data.data
    except Exception as exc:
        log.warning("Gemini TTS failed: %s", exc)
        return None

    audio = _pcm_to_wav(pcm)
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[key] = audio
    return audio
