from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .audio import atomic_json, sha256_file, sha256_text, validate_reference, write_wave
from .config import Settings, load_settings
from .engine import VoxCPMAdapter
from .models import AudioArtifact, VoiceProfile, VoiceRequest, VoiceResult
from .text_chunker import normalize_speech_text, split_text


class VoiceStudio:
    def __init__(self, settings: Settings | None = None, adapter: VoxCPMAdapter | None = None):
        self.settings = settings or load_settings()
        self.adapter = adapter or VoxCPMAdapter(self.settings)

    @classmethod
    def from_env(cls) -> "VoiceStudio":
        return cls(load_settings())

    def _load_profile(self, path: Path) -> VoiceProfile:
        if not path.exists():
            raise FileNotFoundError(f"Voice profile manifest tidak ditemukan: {path}")
        profile = VoiceProfile.model_validate_json(path.read_text(encoding="utf-8"))
        profile.reference_audio_path = profile.reference_audio_path.expanduser().resolve()
        validate_reference(profile.reference_audio_path, self.settings.max_reference_seconds)
        # Consent attestation is checked on every job by VoiceRequest and profile validation.
        return profile

    @staticmethod
    def _load_content_package(path: Path, mode: str) -> tuple[str, list[tuple[str, str]]]:
        if not path.exists():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        content_id = str(data.get("content_id", "")).strip()
        if not content_id:
            raise ValueError("ContentPackage tidak memiliki content_id")
        if data.get("human_review_required", True) and data.get("review_approved") is not True:
            # Require explicit approval only when the package records a required review gate.
            raise ValueError("ContentPackage belum disetujui. Set review_approved=true setelah pemeriksaan manusia.")
        if mode == "scene_voiceovers":
            scenes = data.get("scenes") or []
            items = [(f"scene-{int(s.get('scene_number', i+1)):02d}", str(s.get("voiceover", "")).strip()) for i, s in enumerate(scenes)]
            items = [(name, text) for name, text in items if text]
            if not items:
                raise ValueError("Tidak ada scene voiceover yang dapat disintesis")
            return content_id, items
        narration = str(data.get("narration", "")).strip()
        if not narration:
            raise ValueError("ContentPackage tidak memiliki narration")
        return content_id, [("narration", narration)]

    def synthesize(self, request: VoiceRequest) -> VoiceResult:
        if not request.consent_confirmation:
            raise PermissionError("Konfirmasi izin penggunaan suara wajib")
        profile = self._load_profile(request.voice_profile_path)
        if request.text:
            content_id = request.content_id
            items = [("narration", request.text)]
        else:
            content_id, items = self._load_content_package(request.content_package_path, request.mode)
            if content_id != request.content_id:
                raise ValueError("content_id request tidak sama dengan ContentPackage")
        total_chars = sum(len(text) for _, text in items)
        if total_chars > self.settings.max_text_chars:
            raise ValueError(f"Total teks melewati batas {self.settings.max_text_chars} karakter")

        job_dir = self.settings.output_dir / content_id
        job_dir.mkdir(parents=True, exist_ok=True)
        artifacts: list[AudioArtifact] = []
        pause = np.zeros(int(16000 * self.settings.pause_ms / 1000), dtype=np.float32)
        for item_name, raw_text in items:
            speech = normalize_speech_text(raw_text)
            if not speech:
                continue
            chunks = split_text(speech, self.settings.max_chars_per_chunk)
            waves: list[np.ndarray] = []
            sample_rate: int | None = None
            for index, chunk in enumerate(chunks):
                audio, rate = self.adapter.synthesize_chunk(chunk, profile, request.seed)
                if sample_rate is None:
                    sample_rate = rate
                elif sample_rate != rate:
                    raise RuntimeError("Sample rate model berubah di tengah job")
                waves.append(audio.astype(np.float32, copy=False))
                if index < len(chunks) - 1 and self.settings.pause_ms:
                    pause = np.zeros(int(rate * self.settings.pause_ms / 1000), dtype=np.float32)
                    waves.append(pause)
            if not waves or sample_rate is None:
                raise RuntimeError(f"Tidak ada audio yang dihasilkan untuk {item_name}")
            combined = np.concatenate(waves)
            filename = f"{item_name}.wav" if len(items) > 1 else "narration.wav"
            output_path = job_dir / filename
            stats = write_wave(output_path, combined, sample_rate)
            artifacts.append(AudioArtifact(
                content_id=content_id, segment_id=item_name, audio_path=output_path,
                duration_seconds=stats["duration_seconds"], sample_rate=stats["sample_rate"],
                channels=stats["channels"], sha256=sha256_file(output_path), text_sha256=sha256_text(speech),
            ))

        if not artifacts:
            raise RuntimeError("Voice job tidak menghasilkan artifact")
        metadata_path = job_dir / "voice_manifest.json"
        metadata = {
            "schema_version": "1.0", "content_id": content_id,
            "voice_profile_id": profile.profile_id, "model_id": self.settings.model_id,
            "created_at": datetime.now(timezone.utc).isoformat(), "mode": request.mode,
            "voice_authorization": profile.authorization.model_dump(mode="json"),
            "audio_artifacts": [a.model_dump(mode="json") for a in artifacts],
            "human_audio_review_required": True,
            "review_checklist": ["listen_to_full_audio", "check_indonesian_pronunciation", "check_names_and_numbers", "check_clipping_and_noise", "confirm_voice_rights_and_disclosure"],
        }
        atomic_json(metadata_path, metadata)
        return VoiceResult(content_id=content_id, mode=request.mode, audio_files=artifacts, metadata_path=metadata_path)
