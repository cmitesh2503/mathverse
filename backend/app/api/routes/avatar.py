from fastapi import APIRouter, HTTPException

from ...services.liveavatar_service import LiveAvatarError, liveavatar_service

router = APIRouter(prefix="/avatar", tags=["Avatar"])


@router.get("/liveavatar/status")
def get_liveavatar_status():
    return liveavatar_service.status()


@router.post("/liveavatar/bootstrap")
def bootstrap_liveavatar():
    try:
        session = liveavatar_service.bootstrap_session()
    except LiveAvatarError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return {
        "provider": "liveavatar",
        "configured": True,
        "session_token": session.session_token,
        "session_id": session.session_id,
        "livekit_url": session.livekit_url,
        "livekit_client_token": session.livekit_client_token,
        "embed_url": session.embed_url,
    }
