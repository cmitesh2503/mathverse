from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..core.config import (
    LIVEAVATAR_API_BASE,
    LIVEAVATAR_API_KEY,
    LIVEAVATAR_AUTO_START,
    LIVEAVATAR_AVATAR_ID,
    LIVEAVATAR_CONTEXT_ID,
    LIVEAVATAR_EMBED_BASE,
    LIVEAVATAR_IS_SANDBOX,
    LIVEAVATAR_LANGUAGE,
    LIVEAVATAR_MODE,
    LIVEAVATAR_SPEECH_SPEED,
    LIVEAVATAR_VOICE_ID,
)


class LiveAvatarError(RuntimeError):
    pass


@dataclass
class LiveAvatarSession:
    session_token: str
    session_id: str | None
    livekit_url: str
    livekit_client_token: str
    embed_url: str


class LiveAvatarService:
    def __init__(self) -> None:
        self.api_base = LIVEAVATAR_API_BASE.rstrip("/")

    @property
    def configured(self) -> bool:
        return not self.missing_fields

    @property
    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        required = {
            "LIVEAVATAR_API_KEY": LIVEAVATAR_API_KEY,
            "LIVEAVATAR_AVATAR_ID": LIVEAVATAR_AVATAR_ID,
            "LIVEAVATAR_CONTEXT_ID": LIVEAVATAR_CONTEXT_ID,
            "LIVEAVATAR_VOICE_ID": LIVEAVATAR_VOICE_ID,
        }
        for key, value in required.items():
            if not value:
                missing.append(key)
        return missing

    def status(self) -> dict[str, Any]:
        return {
            "provider": "liveavatar",
            "configured": self.configured,
            "auto_start": LIVEAVATAR_AUTO_START,
            "mode": LIVEAVATAR_MODE,
            "is_sandbox": LIVEAVATAR_IS_SANDBOX,
            "language": LIVEAVATAR_LANGUAGE,
            "speech_speed": LIVEAVATAR_SPEECH_SPEED,
            "missing_fields": self.missing_fields,
            "setup_hint": (
                "Set LIVEAVATAR_API_KEY, LIVEAVATAR_AVATAR_ID, LIVEAVATAR_CONTEXT_ID, "
                "and LIVEAVATAR_VOICE_ID in your backend environment to launch the human avatar."
            ),
        }

    def bootstrap_session(self) -> LiveAvatarSession:
        if not self.configured:
            raise LiveAvatarError(
                f"LiveAvatar is not configured. Missing: {', '.join(self.missing_fields)}"
            )

        token_response = self._create_session_token()
        session_token = self._read_str(token_response, "session_token", "token")
        if not session_token:
            raise LiveAvatarError("LiveAvatar did not return a session token.")

        start_response = self._start_session(session_token)
        livekit_url = self._read_str(start_response, "livekit_url", "url")
        livekit_client_token = self._read_str(
            start_response,
            "livekit_client_token",
            "token",
            "livekit_token",
        )
        if not livekit_url or not livekit_client_token:
            raise LiveAvatarError("LiveAvatar did not return LiveKit connection data.")

        query = urlencode(
            {
                "liveKitUrl": livekit_url,
                "token": livekit_client_token,
            }
        )

        return LiveAvatarSession(
            session_token=session_token,
            session_id=self._read_str(start_response, "session_id", "id"),
            livekit_url=livekit_url,
            livekit_client_token=livekit_client_token,
            embed_url=f"{LIVEAVATAR_EMBED_BASE}?{query}",
        )

    def _create_session_token(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "mode": LIVEAVATAR_MODE,
            "avatar_id": LIVEAVATAR_AVATAR_ID,
            "avatar_persona": {
                "voice_id": LIVEAVATAR_VOICE_ID,
                "context_id": LIVEAVATAR_CONTEXT_ID,
                "language": LIVEAVATAR_LANGUAGE,
                "voice_quality": {
                    "speed": LIVEAVATAR_SPEECH_SPEED,
                },
            },
        }
        if LIVEAVATAR_IS_SANDBOX:
            payload["is_sandbox"] = True

        return self._post(
            "/v1/sessions/token",
            payload,
            headers={"X-API-KEY": LIVEAVATAR_API_KEY or ""},
        )

    def _start_session(self, session_token: str) -> dict[str, Any]:
        return self._post(
            "/v1/sessions/start",
            {},
            headers={"Authorization": f"Bearer {session_token}"},
        )

    def _post(self, path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = Request(
            url=f"{self.api_base}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                **headers,
            },
        )

        try:
            with urlopen(request, timeout=25) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except Exception as error:  # pragma: no cover - network dependent
            raise LiveAvatarError(f"LiveAvatar request failed: {error}") from error

        if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
            return raw["data"]
        return raw

    def _read_str(self, payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None


liveavatar_service = LiveAvatarService()
