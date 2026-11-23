from __future__ import annotations

import hmac
import os
import re
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .config import load_settings
from .models import VoiceRequest
from .studio import VoiceStudio

app = FastAPI(title="VYRO AI Voice Studio API", version="1.1.0")

def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

class VoiceJob(BaseModel):
    content_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    text: str = Field(min_length=1, max_length=12000)
    voice_profile_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    consent_confirmation: bool = False
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-ai-voice-studio", "status": "ok", "version": "1.1.0"}

@app.post("/v1/voice/synthesize", dependencies=[Depends(require_service_key)])
def synthesize(payload: VoiceJob) -> dict:
    if not payload.consent_confirmation:
        raise HTTPException(status_code=403, detail="Konfirmasi izin penggunaan suara wajib")
    settings = load_settings()
    profile_path = (settings.profile_dir / f"{payload.voice_profile_id}.json").resolve()
    if settings.profile_dir.resolve() not in profile_path.parents:
        raise HTTPException(status_code=400, detail="Voice profile path tidak valid")
    if not profile_path.is_file():
        raise HTTPException(status_code=404, detail="Voice profile tidak ditemukan")
    try:
        request = VoiceRequest(content_id=payload.content_id, text=payload.text, voice_profile_path=profile_path, seed=payload.seed, consent_confirmation=True)
        result = VoiceStudio(settings=settings).synthesize(request)
    except (ValidationError, ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    artifacts = []
    for item in result.audio_files:
        artifacts.append({
            "segment_id": item.segment_id, "filename": item.audio_path.name,
            "duration_seconds": item.duration_seconds, "sample_rate": item.sample_rate,
            "channels": item.channels, "sha256": item.sha256,
            "download_url": f"/v1/voice/files/{payload.content_id}/{item.audio_path.name}",
        })
    return {"content_id": result.content_id, "mode": result.mode, "audio_files": artifacts, "human_audio_review_required": True}

@app.get("/v1/voice/files/{content_id}/{filename}", dependencies=[Depends(require_service_key)])
def download_audio(content_id: str, filename: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", content_id) or filename not in {"narration.wav"} and not re.fullmatch(r"scene-[0-9]{2}\.wav", filename):
        raise HTTPException(status_code=400, detail="Artifact ID tidak valid")
    output_root = load_settings().output_dir.resolve()
    path = (output_root / content_id / filename).resolve()
    if output_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Audio tidak ditemukan")
    return FileResponse(path, media_type="audio/wav", filename=filename)
