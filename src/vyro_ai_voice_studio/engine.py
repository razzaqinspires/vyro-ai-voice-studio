from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

from .config import Settings, load_settings
from .models import VoiceProfile


class VoxCPMAdapter:
    """Lazy, serialized wrapper around the official VoxCPM Python API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._model: Any | None = None
        self._lock = threading.RLock()

    def load(self) -> Any:
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from voxcpm import VoxCPM
            except ImportError as exc:
                raise RuntimeError("VoxCPM belum terpasang. Instal dengan: pip install -e '.[engine]'") from exc
            optimize_setting = self.settings.optimize.lower()
            if optimize_setting == "auto":
                try:
                    import torch
                    optimize = bool(torch.cuda.is_available())
                except ImportError:
                    optimize = False
            else:
                optimize = optimize_setting in {"1", "true", "yes", "on"}
            self._model = VoxCPM.from_pretrained(
                self.settings.model_id,
                load_denoiser=False,
                device=self.settings.device,
                optimize=optimize,
            )
            return self._model

    def synthesize_chunk(self, text: str, profile: VoiceProfile, seed: int | None = None) -> tuple[np.ndarray, int]:
        model = self.load()
        kwargs: dict[str, Any] = {
            "text": text,
            "reference_wav_path": str(profile.reference_audio_path),
            "cfg_value": self.settings.cfg_value,
            "inference_timesteps": self.settings.inference_timesteps,
            "normalize": self.settings.normalize,
            "denoise": self.settings.denoise,
            "retry_badcase": self.settings.retry_badcase,
            "retry_badcase_max_times": self.settings.retry_badcase_max_times,
            "retry_badcase_ratio_threshold": self.settings.retry_badcase_ratio_threshold,
        }
        # Continuation conditioning is optional and only used when an exact reference transcript exists.
        if profile.reference_transcript.strip():
            kwargs["prompt_wav_path"] = str(profile.reference_audio_path)
            kwargs["prompt_text"] = profile.reference_transcript.strip()
        if seed is not None:
            kwargs["seed"] = seed
        with self._lock:
            generated = model.generate(**kwargs)
        audio = np.asarray(generated, dtype=np.float32).reshape(-1)
        if audio.size == 0:
            raise RuntimeError("VoxCPM mengembalikan waveform kosong")
        sample_rate = int(getattr(getattr(model, "tts_model", None), "sample_rate", 16000))
        if sample_rate <= 0:
            raise RuntimeError("VoxCPM sample rate tidak valid")
        return audio, sample_rate
