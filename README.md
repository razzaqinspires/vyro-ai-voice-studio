# VYRO AI Voice Studio

**Version:** 1.0.0  
**Role:** Dedicated voice and speech subsystem for VYRO's content pipeline.  
**Primary runtime:** VoxCPM2 local TTS. Optional faster-whisper transcription and generated-audio QA.

This repository was separated from the voice subsystem in the uploaded **ARIFI MOTION STUDIO** project. It preserves the source workflow—reference-conditioned VoxCPM2 synthesis and optional Whisper transcription—while making it independent, configurable, testable, and easier for a future orchestrator to call.

## Scope and boundaries

This component accepts either a plain voice request or a compatible VYRO `ContentPackage`, resolves an authorized voice profile, synthesizes WAV audio, records provenance, and optionally transcribes the generated result for QA.

It does not generate scripts, create video, schedule posts, or publish to Instagram. The AI Content Engine supplies narration/scene voiceover text; the Video Render Engine consumes this repository's audio artifact.

## Key improvements over the Motion Studio copy

- Independent package, CLI, configuration, storage, tests, and integration contract.
- Explicit voice-use authorization check before synthesis.
- Robust sentence-aware chunking with word-boundary fallback.
- Correct current VoxCPM2 `generate()` result handling and configurable inference options.
- One lazy-loaded model instance and serialized GPU inference per process.
- Audio file validation, duration/sample-rate metadata, SHA-256 provenance, and deterministic job IDs.
- Optional faster-whisper transcription QA; ASR is not required for TTS.
- Safe output paths and atomic metadata writes.
- No raw voice references or generated audio are intended for Git.

## Install

Base package:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Install the local TTS runtime only after checking the PyTorch/CUDA combination for your device:

```bash
pip install -e '.[engine,dev]'
```

Optional speech recognition QA:

```bash
pip install -e '.[asr]'
```

FFmpeg and ffprobe are recommended for reference-audio normalization. VoxCPM2's initial model download is large; model weights are not included in Git.

## Voice profile and consent

Copy `examples/voice_profile.example.json` and provide:

- a local path to a clean reference recording;
- the exact words spoken in that recording;
- `rights_confirmed: true` only when the voice belongs to you or the speaker has explicitly authorized this use;
- a consent scope and consent record identifier/date.

The program validates an explicit consent attestation; it cannot independently verify a speaker's identity or legal consent. Do not clone a third party's voice without permission. Keep original samples and voice profiles private.

Practical reference guidance: clean, single-speaker audio without music or strong reverberation is preferred. The original Motion Studio used a 2–180 second acceptance window; for voice likeness and exact transcript alignment, start with a clean 5–30 second sample and inspect the generated audio. In this release, the reference recording supplies the speaker characteristics; there is no separate controllable emotion/prosody parameter exposed by this adapter.

## Create a local voice profile

Normalize a reference recording and create a profile manifest. The command requires an explicit rights confirmation; it cannot verify the speaker's identity or legal consent for you.

```bash
vyro-voice create-profile \
  --audio ./voice_samples/authorized_sample.wav \
  --profile-id vyro-main-voice \
  --transcript "Exact words spoken in the reference recording." \
  --relationship self \
  --consent-record-id consent-2026-001 \
  --consent-scope "Local voice synthesis for VYRO MEDIA content" \
  --consent-date 2026-11-23 \
  --rights-confirmed
```

Use `--relationship authorized_speaker` only when another speaker has explicitly granted permission. Set `--expiry-date` when authorization has a known end date.

## Generate from a VYRO ContentPackage

The voice engine accepts the `narration` field or scene-level `voiceover` fields. By default it uses full narration. Use scene mode when separate audio clips are needed for video editing.

```bash
vyro-voice validate examples/voice_request.example.json
vyro-voice synthesize examples/voice_request.example.json --output outputs/demo.wav
```

Use `--scene-voiceovers` to synthesize one WAV per scene from scene `voiceover` strings.

## Python API

```python
from vyro_ai_voice_studio.studio import VoiceStudio
from vyro_ai_voice_studio.models import VoiceRequest

studio = VoiceStudio.from_env()
request = VoiceRequest.model_validate_json(open("voice_request.json", encoding="utf-8").read())
result = studio.synthesize(request)
print(result.audio_path, result.duration_seconds)
```

## Optional transcription QA

```bash
vyro-voice transcribe outputs/demo.wav --language id
```

Whisper output is a QA aid. It is not a definitive measure of pronunciation quality; a human must listen to the audio and check names, numbers, brand names, and Indonesian articulation.

## Hardware and operating limits

VoxCPM2 is a multi-gigabyte model. GPU acceleration is preferred; CPU fallback can be very slow and may not fit typical mobile phones. This is designed as a local workstation/server component, not as a claim that synthesis can run comfortably on every Android handset.

## Quality checks

```bash
ruff check .
pytest
```

## References

The adapter follows the current upstream non-streaming API: `VoxCPM.from_pretrained(...)` and `model.generate(...)` return a waveform array; `reference_wav_path` is the voice-reference input and `prompt_wav_path` must be paired with its exact `prompt_text`. Model generation options such as normalization, denoising, bad-case retry, guidance, inference steps, and seed are configurable where supported by the installed VoxCPM version.


- VoxCPM2 model card and current usage: https://huggingface.co/openbmb/VoxCPM2
- VoxCPM Python API: https://github.com/OpenBMB/VoxCPM
- faster-whisper: https://github.com/SYSTRAN/faster-whisper

## 1.1.0 — Prime API
Optional FastAPI service exposes `POST /v1/voice/synthesize` and protected WAV downloads. It accepts a server-configured `voice_profile_id`, not an arbitrary filesystem path. Install `pip install -e '.[api]'`, set `VYRO_SERVICE_API_KEY`, `VOICE_PROFILE_DIR`, and model settings, then run `uvicorn vyro_ai_voice_studio.api:app --host 0.0.0.0 --port 8000`. Every request must affirm consent; the profile manifest must also contain valid rights metadata. Audio still requires human listening QA.
