# Security Policy

- Only synthesize voices owned by the operator or supported by explicit, documented authorization.
- Store reference audio and voice profile manifests outside Git and restrict filesystem access.
- Do not commit voice samples, WAV outputs, credentials, or consent records containing personal data.
- Browser demo IDs are namespaces, not authentication.
- Listen to the complete generated audio and review consent scope before reuse.
