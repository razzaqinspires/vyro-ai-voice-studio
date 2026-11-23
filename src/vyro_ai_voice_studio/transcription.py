from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .config import Settings, load_settings


class Transcriber:
    """Optional lazy faster-whisper wrapper; no model is loaded until transcription is requested."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self._model: Any | None = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("ASR belum terpasang. Jalankan: pip install -e '.[asr]'") from exc
            device = self.settings.whisper_device
            compute = self.settings.whisper_compute_type
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
            if compute == "auto":
                compute = "float16" if device == "cuda" else "int8"
            self._model = WhisperModel(self.settings.whisper_model, device=device, compute_type=compute)
            return self._model

    def transcribe(self, audio_path: Path, language: str | None = None) -> dict[str, Any]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        model = self._load()
        segments, info = model.transcribe(str(audio_path), language=language, beam_size=5,
                                          vad_filter=True, condition_on_previous_text=True)
        rows = []
        text_parts = []
        for segment in segments:
            piece = segment.text.strip()
            if piece:
                text_parts.append(piece)
                rows.append({"start": round(float(segment.start), 2), "end": round(float(segment.end), 2), "text": piece})
        return {"text": " ".join(text_parts).strip(), "language": getattr(info, "language", None),
                "language_probability": round(float(getattr(info, "language_probability", 0.0)), 3), "segments": rows}
