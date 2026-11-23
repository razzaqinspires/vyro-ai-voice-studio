# VYRO AI Voice Studio

**Release:** 1.2.0 · **Python:** 3.11+ · **Engine:** VoxCPM2 (optional runtime dependency).

## Responsibilities
- Synthesize Indonesian narration from a server-configured, rights-cleared voice profile.
- Normalize and validate reference audio; split long narration into stable chunks.
- Produce WAV artifacts and provenance manifests (audio hash and text hash).
- Optionally transcribe output with faster-whisper for QA.

The service does not create scripts, images, videos, or Instagram posts. `vyro-ai-content-engine` supplies narration text; `vyro-video-render-engine` consumes the resulting WAV.

## API
- `GET /health`
- `POST /v1/voice/synthesize`
- `GET /v1/voice/files/{demo_id}/{content_id}/{filename}`

All routes except health require the service bearer token. `demo_id` is a temporary browser namespace, not identity verification. Artifacts are isolated by a hash of the demo ID and expire after `VOICE_ARTIFACT_RETENTION_HOURS` (default 48).

## Profile compatibility
Create profiles with `vyro-voice create-profile`; the API resolves `<VOICE_PROFILE_DIR>/<profile_id>/voice_profile.json`. Profile authorization is checked by the voice engine; a browser checkbox alone cannot authorize a voice profile.

## Install
```bash
pip install -e '.[api,engine,dev]'
uvicorn vyro_ai_voice_studio.api:app --host 0.0.0.0 --port 8103
pytest -q
```

Model weights and hardware requirements are not bundled. Validate the VoxCPM model version, VRAM/RAM requirements, sample rate, and Indonesian pronunciation on the target host before accepting paid jobs.
