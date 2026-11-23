# Integration Contract: AI Content Engine → AI Voice Studio

The AI Content Engine is responsible for producing approved text. The Voice Studio is responsible only for speech synthesis and audio metadata.

## Accepted input

Preferred: the JSON export of `vyro_ai_content_engine.models.ContentPackage` with:
- `content_id`
- `narration`
- optional `scenes[].scene_number`
- optional `scenes[].voiceover`
- `human_review_required`
- `review_approved: true`, set by a human reviewer only after checking the package. The AI Content Engine always emits `review_approved: false`.

## Request example

```json
{
  "content_id": "vyro-umkm-001",
  "content_package_path": "./approved/content-package.json",
  "voice_profile_path": "./voice_profiles/voice-owner-main.json",
  "mode": "narration",
  "consent_confirmation": true
}
```

`mode="scene_voiceovers"` creates one WAV per scene with non-empty `voiceover` text.

## Output

- One narration WAV or a set of per-scene WAV files.
- `voice_manifest.json` containing IDs, timestamps, model name, audio metadata, SHA-256 hashes, and mandatory human review checklist.
- No automatic approval is ever inferred from successful synthesis.

## Human gates

1. An editor sets `review_approved=true` in the approved content package after factual and brand review.
2. An authorized voice user confirms consent for each job.
3. The resulting audio is listened to and checked before it enters the renderer.
