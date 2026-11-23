from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    model_id: str = "openbmb/VoxCPM2"
    device: str = "auto"
    optimize: str = "auto"
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    normalize: bool = True
    denoise: bool = False
    retry_badcase: bool = True
    retry_badcase_max_times: int = 2
    retry_badcase_ratio_threshold: float = 6.0
    max_chars_per_chunk: int = 360
    pause_ms: int = 280
    max_text_chars: int = 12000
    max_reference_seconds: int = 180
    output_dir: Path = Path("outputs")
    profile_dir: Path = Path("voice_profiles")
    asr_enabled: bool = False
    whisper_model: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        model_id=os.getenv("VOXCPM_MODEL", "openbmb/VoxCPM2"),
        device=os.getenv("VOXCPM_DEVICE", "auto"),
        optimize=os.getenv("VOXCPM_OPTIMIZE", "auto"),
        cfg_value=float(os.getenv("VOXCPM_CFG_VALUE", "2.0")),
        inference_timesteps=max(1, min(int(os.getenv("VOXCPM_INFERENCE_TIMESTEPS", "10")), 50)),
        normalize=os.getenv("VOXCPM_NORMALIZE", "true").lower() in {"1","true","yes","on"},
        denoise=os.getenv("VOXCPM_DENOISE", "false").lower() in {"1","true","yes","on"},
        retry_badcase=os.getenv("VOXCPM_RETRY_BADCASE", "true").lower() in {"1","true","yes","on"},
        retry_badcase_max_times=max(0, min(int(os.getenv("VOXCPM_RETRY_BADCASE_MAX_TIMES", "2")), 5)),
        retry_badcase_ratio_threshold=max(1.0, float(os.getenv("VOXCPM_RETRY_BADCASE_RATIO_THRESHOLD", "6.0"))),
        max_chars_per_chunk=max(80, min(int(os.getenv("VOXCPM_MAX_CHARS_PER_CHUNK", "360")), 1000)),
        pause_ms=max(0, min(int(os.getenv("VOICE_PAUSE_MS", "280")), 2000)),
        max_text_chars=max(100, min(int(os.getenv("VOICE_MAX_TEXT_CHARS", "12000")), 50000)),
        max_reference_seconds=max(5, min(int(os.getenv("VOICE_MAX_REFERENCE_SECONDS", "180")), 600)),
        output_dir=Path(os.getenv("VOICE_OUTPUT_DIR", "./outputs")).expanduser().resolve(),
        profile_dir=Path(os.getenv("VOICE_PROFILE_DIR", "./voice_profiles")).expanduser().resolve(),
        asr_enabled=os.getenv("VOICE_ASR_ENABLED", "false").lower() in {"1","true","yes","on"},
        whisper_model=os.getenv("WHISPER_MODEL", "base"),
        whisper_device=os.getenv("WHISPER_DEVICE", "auto"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "auto"),
    )
