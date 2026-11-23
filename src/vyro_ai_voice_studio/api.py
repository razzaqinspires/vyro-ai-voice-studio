from __future__ import annotations

import hmac
import os
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import load_settings
from .demo_scope import demo_namespace
from .models import VoiceRequest
from .profile_store import resolve_voice_profile
from .studio import VoiceStudio

APP_VERSION = "1.2.0"
app = FastAPI(title="VYRO AI Voice Studio API", version=APP_VERSION)


def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class VoiceJob(BaseModel):
    demo_id: str = Field(pattern=r"^VYRO-DEMO-[A-Fa-f0-9]{8,40}$")
    content_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    text: str = Field(min_length=1, max_length=12000)
    voice_profile_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    consent_confirmation: bool = False
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-ai-voice-studio", "status": "ok", "version": APP_VERSION}


@app.post("/v1/voice/synthesize", dependencies=[Depends(require_service_key)])
def synthesize(payload: VoiceJob) -> dict:
    if not payload.consent_confirmation:
        raise HTTPException(status_code=403, detail="Konfirmasi izin penggunaan suara wajib")
    try:
        namespace = demo_namespace(payload.demo_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    settings = load_settings()
    # CLI-created profiles are stored in <profile_dir>/<id>/voice_profile.json.
    try:
        profile_path = resolve_voice_profile(settings.profile_dir, payload.voice_profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if profile_path is None:
        raise HTTPException(status_code=404, detail="Voice profile tidak ditemukan")

    scoped_settings = replace(settings, output_dir=(settings.output_dir / namespace).resolve())
    try:
        request = VoiceRequest(
            content_id=payload.content_id, text=payload.text, voice_profile_path=profile_path,
            seed=payload.seed, consent_confirmation=True,
        )
        result = VoiceStudio(settings=scoped_settings).synthesize(request)
    except (ValueError, PermissionError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    artifacts = []
    for item in result.audio_files:
        artifacts.append({
            "segment_id": item.segment_id,
            "filename": item.audio_path.name,
            "duration_seconds": item.duration_seconds,
            "sample_rate": item.sample_rate,
            "channels": item.channels,
            "sha256": item.sha256,
            "download_url": f"/v1/voice/files/{payload.demo_id}/{payload.content_id}/{item.audio_path.name}",
        })
    return {
        "demo_id": payload.demo_id,
        "content_id": result.content_id,
        "mode": result.mode,
        "audio_files": artifacts,
        "human_audio_review_required": True,
        "expires_after_hours": int(os.getenv("VOICE_ARTIFACT_RETENTION_HOURS", "48")),
    }


@app.get("/v1/voice/files/{demo_id}/{content_id}/{filename}", dependencies=[Depends(require_service_key)])
def download_audio(demo_id: str, content_id: str, filename: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", content_id) or (filename != "narration.wav" and not re.fullmatch(r"scene-[0-9]{2}\.wav", filename)):
        raise HTTPException(status_code=400, detail="Artifact ID tidak valid")
    settings = load_settings()
    try:
        namespace = demo_namespace(demo_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    output_root = (settings.output_dir / namespace).resolve()
    path = (output_root / content_id / filename).resolve()
    if output_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Audio tidak ditemukan atau sudah kedaluwarsa")
    retention_hours = max(1, min(int(os.getenv("VOICE_ARTIFACT_RETENTION_HOURS", "48")), 720))
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if (datetime.now(timezone.utc) - modified).total_seconds() > retention_hours * 3600:
        shutil.rmtree(path.parent, ignore_errors=True)
        raise HTTPException(status_code=410, detail="Audio demo telah kedaluwarsa")
    return FileResponse(path, media_type="audio/wav", filename=filename)
