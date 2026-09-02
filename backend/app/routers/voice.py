from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import settings
from app.schemas import TtsIn, TtsStatusOut, TtsVoicePack
from app.services.doubao_tts import (
    is_doubao_tts_configured,
    list_voice_packs,
    resolve_speaker,
    synthesize_speech,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/status", response_model=TtsStatusOut)
def tts_status():
    configured = is_doubao_tts_configured()
    provider = settings.tts_provider or "auto"
    effective = "doubao" if configured and provider != "browser" else "browser"
    voices = [TtsVoicePack(**v) for v in list_voice_packs()]
    return TtsStatusOut(
        provider=provider,
        effective=effective,
        doubao_configured=configured,
        speaker=resolve_speaker() if configured else "",
        voices=voices,
    )


@router.get("/voices", response_model=list[TtsVoicePack])
def list_voices():
    return [TtsVoicePack(**v) for v in list_voice_packs()]


@router.post("/tts")
async def text_to_speech(body: TtsIn):
    if not (body.text or "").strip():
        raise HTTPException(400, "text 不能为空")
    if not is_doubao_tts_configured():
        raise HTTPException(503, "豆包 TTS 未配置，请填写 DOUBAO_TTS_APP_ID / ACCESS_KEY")
    try:
        audio = await synthesize_speech(body.text.strip(), speaker=body.speaker)
    except Exception as e:
        raise HTTPException(502, f"豆包 TTS 合成失败: {e}") from e
    return Response(content=audio, media_type="audio/mpeg")
