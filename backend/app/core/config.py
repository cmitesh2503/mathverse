import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_TEXT_MODEL = "gemini-2.5-flash-lite"
_DEPRECATED_GEMINI_TEXT_MODELS = {
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
}
_configured_text_model = os.getenv("GEMINI_TEXT_MODEL", DEFAULT_GEMINI_TEXT_MODEL).strip()
GEMINI_TEXT_MODEL = (
    FALLBACK_GEMINI_TEXT_MODEL
    if _configured_text_model in _DEPRECATED_GEMINI_TEXT_MODELS
    else (_configured_text_model or DEFAULT_GEMINI_TEXT_MODEL)
)
DEFAULT_GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
_configured_live_model = os.getenv("GEMINI_LIVE_MODEL", DEFAULT_GEMINI_LIVE_MODEL).strip()
GEMINI_LIVE_MODEL = (
    _configured_live_model
    if "live" in _configured_live_model.lower() or "native-audio" in _configured_live_model.lower()
    else DEFAULT_GEMINI_LIVE_MODEL
)
GEMINI_LIVE_VOICE = os.getenv("GEMINI_LIVE_VOICE", "Puck")
GEMINI_LIVE_INPUT_LANGUAGE = os.getenv("GEMINI_LIVE_INPUT_LANGUAGE", "en-IN")
GEMINI_LIVE_OUTPUT_LANGUAGE = os.getenv("GEMINI_LIVE_OUTPUT_LANGUAGE", "en-IN")


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


LIVEAVATAR_API_BASE = os.getenv("LIVEAVATAR_API_BASE", "https://api.liveavatar.com")
LIVEAVATAR_EMBED_BASE = os.getenv(
    "LIVEAVATAR_EMBED_BASE",
    "https://meet.livekit.io/custom",
)
LIVEAVATAR_API_KEY = os.getenv("LIVEAVATAR_API_KEY")
LIVEAVATAR_AVATAR_ID = os.getenv("LIVEAVATAR_AVATAR_ID")
LIVEAVATAR_CONTEXT_ID = os.getenv("LIVEAVATAR_CONTEXT_ID")
LIVEAVATAR_VOICE_ID = os.getenv("LIVEAVATAR_VOICE_ID")
LIVEAVATAR_LANGUAGE = os.getenv("LIVEAVATAR_LANGUAGE", "en")
LIVEAVATAR_MODE = os.getenv("LIVEAVATAR_MODE", "FULL")
LIVEAVATAR_IS_SANDBOX = _env_flag("LIVEAVATAR_IS_SANDBOX", default=True)
LIVEAVATAR_AUTO_START = _env_flag("LIVEAVATAR_AUTO_START", default=False)

_speed_value = os.getenv("LIVEAVATAR_SPEECH_SPEED")
try:
    LIVEAVATAR_SPEECH_SPEED = float(_speed_value) if _speed_value else 0.55
except ValueError:
    LIVEAVATAR_SPEECH_SPEED = 0.55
