from fastapi import (
    APIRouter,
    UploadFile,
    File
)

from app.services.jee.voice_tutor import (
    transcribe_audio
)

router = APIRouter()

@router.post("/voice")
async def voice_chat(
    audio: UploadFile = File(...)
):

    audio_bytes = await audio.read()

    transcript = transcribe_audio(
        audio_bytes
    )

    return {
        "transcript": transcript
    }