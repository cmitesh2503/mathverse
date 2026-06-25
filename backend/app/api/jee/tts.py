from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import Response

from app.services.tts_service import (
    synthesize_speech
)

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
async def tts(
    request: TTSRequest
):

    audio = synthesize_speech(
        request.text
    )

    return Response(
        content=audio,
        media_type="audio/mpeg"
    )