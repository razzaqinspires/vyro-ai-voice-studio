from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf


class AudioError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def probe_duration(path: Path) -> float:
    if not path.is_file():
        raise FileNotFoundError(path)
    if shutil.which("ffprobe"):
        completed = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if completed.returncode == 0:
            try:
                duration = float(completed.stdout.strip())
                if duration > 0:
                    return duration
            except ValueError:
                pass
    info = sf.info(path)
    if info.samplerate <= 0 or info.frames <= 0:
        raise AudioError("File audio tidak memiliki frame/sample rate yang valid")
    return info.frames / info.samplerate


def validate_reference(path: Path, max_seconds: int) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File reference voice tidak ditemukan: {path}")
    info = sf.info(path)
    duration = probe_duration(path)
    if duration < 2.0:
        raise AudioError("Sampel referensi minimal 2 detik")
    if duration > max_seconds:
        raise AudioError(f"Sampel referensi melebihi batas {max_seconds} detik")
    if info.channels > 2:
        raise AudioError("Sampel referensi maksimal stereo (2 channel)")
    if info.samplerate < 8000 or info.samplerate > 96000:
        raise AudioError("Sample rate referensi harus berada di rentang 8–96 kHz")
    return {"duration_seconds": round(duration, 3), "sample_rate": info.samplerate, "channels": info.channels, "subtype": info.subtype}


def normalize_reference(source: Path, target: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise AudioError("FFmpeg tidak ditemukan. Pasang FFmpeg untuk normalisasi reference audio.")
    target.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)],
        capture_output=True, text=True, timeout=180, check=False,
    )
    if completed.returncode != 0 or not target.exists():
        raise AudioError(f"FFmpeg gagal menormalisasi audio: {(completed.stderr or '')[-1000:]}")
    return target


def write_wave(path: Path, samples: np.ndarray, sample_rate: int) -> dict[str, Any]:
    arr = np.asarray(samples, dtype=np.float32).reshape(-1)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise AudioError("Waveform kosong atau mengandung nilai non-finite")
    peak = float(np.max(np.abs(arr)))
    if peak > 1.0:
        arr = arr / peak * 0.98
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    sf.write(tmp, arr, sample_rate, subtype="PCM_16", format="WAV")
    tmp.replace(path)
    info = sf.info(path)
    return {"duration_seconds": round(info.frames / info.samplerate, 3), "sample_rate": info.samplerate, "channels": info.channels}


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
