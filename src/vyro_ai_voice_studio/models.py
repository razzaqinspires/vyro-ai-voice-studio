from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoiceAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rights_confirmed: bool = False
    subject_relationship: Literal["self", "authorized_speaker"]
    consent_record_id: str = Field(min_length=4, max_length=100)
    consent_scope: str = Field(min_length=8, max_length=500)
    consent_date: str = Field(min_length=8, max_length=40)
    expiry_date: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def require_rights(self):
        if not self.rights_confirmed:
            raise ValueError("Hak penggunaan suara belum dikonfirmasi")
        try:
            consent = datetime.fromisoformat(self.consent_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("consent_date harus berupa tanggal ISO-8601") from exc
        if consent.tzinfo is None:
            consent = consent.replace(tzinfo=timezone.utc)
        if consent > datetime.now(timezone.utc):
            raise ValueError("consent_date tidak boleh berada di masa depan")
        if self.expiry_date:
            try:
                expiry = datetime.fromisoformat(self.expiry_date.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("expiry_date harus berupa tanggal ISO-8601") from exc
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc):
                raise ValueError("Izin penggunaan suara telah kedaluwarsa")
            if expiry <= consent:
                raise ValueError("expiry_date harus setelah consent_date")
        return self


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
    reference_audio_path: Path
    reference_transcript: str = Field(min_length=5, max_length=1500)
    language: str = Field(default="id-ID", max_length=20)
    authorization: VoiceAuthorization

    @field_validator("profile_id")
    @classmethod
    def prevent_path_traversal(cls, value: str) -> str:
        if ".." in value or value.startswith("."):
            raise ValueError("profile_id tidak boleh mengandung path traversal")
        return value


class VoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    text: str | None = Field(default=None, max_length=12000)
    content_package_path: Path | None = None
    voice_profile_path: Path
    mode: Literal["narration", "scene_voiceovers"] = "narration"
    seed: int | None = Field(default=None, ge=0, le=2**31-1)
    consent_confirmation: bool = False

    @field_validator("content_id")
    @classmethod
    def prevent_content_path_traversal(cls, value: str) -> str:
        if ".." in value or value.startswith("."):
            raise ValueError("content_id tidak boleh mengandung path traversal")
        return value

    @model_validator(mode="after")
    def validate_source(self):
        if not self.text and not self.content_package_path:
            raise ValueError("Isi text atau content_package_path wajib tersedia")
        if self.text and self.content_package_path:
            raise ValueError("Gunakan text atau content_package_path, bukan keduanya")
        if not self.consent_confirmation:
            raise ValueError("Konfirmasi izin penggunaan suara wajib aktif pada setiap job")
        return self


class AudioArtifact(BaseModel):
    content_id: str
    segment_id: str
    audio_path: Path
    duration_seconds: float = Field(gt=0)
    sample_rate: int = Field(gt=0)
    channels: int = Field(ge=1, le=2)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class VoiceResult(BaseModel):
    content_id: str
    mode: str
    audio_files: list[AudioArtifact]
    metadata_path: Path
    human_audio_review_required: bool = True
