from pathlib import Path
import numpy as np
import soundfile as sf
from vyro_ai_voice_studio.audio import sha256_file, sha256_text, write_wave


def test_write_wave_and_hashes(tmp_path: Path):
    target = tmp_path / "tone.wav"
    stats = write_wave(target, np.zeros(16000, dtype=np.float32), 16000)
    assert stats["sample_rate"] == 16000
    assert target.exists()
    assert len(sha256_file(target)) == 64
    assert len(sha256_text("hello")) == 64
