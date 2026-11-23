# Security Policy

## Voice data is sensitive

Voice recordings and derived profiles can identify a person. Keep samples, profiles, generated audio, transcripts, and manifests on storage controlled by the authorized user. Do not commit or upload them to public issue trackers.

## Required controls

- Only synthesize a voice you own or are explicitly authorized to use.
- Keep `.env`, model weights, reference audio, and generated files out of Git.
- Use local filesystem permissions and disk encryption where available.
- Avoid sending private voice samples to unapproved cloud providers.
- Delete reference samples and profile metadata when consent expires or is withdrawn.
- Never use the engine to impersonate a person, deceive listeners, bypass verification, or fabricate endorsements.
- Treat generated output as synthetic media and disclose it where law/platform policy requires.

## Reporting

Privately report security issues to the repository maintainer. Do not include voice recordings, tokens, or personal identifiers in public reports.
