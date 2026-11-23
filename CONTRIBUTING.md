# Contributing

- Keep model imports lazy so validation and unit tests work without downloading GPU packages.
- Put model-specific behavior in the VoxCPM adapter.
- Add deterministic tests with fake model objects; do not require a GPU for the default test suite.
- Never add reference voices, private transcripts, generated audio, or model checkpoints.
- Preserve content ID and the exact approved narration text in metadata.
- Run `ruff check .` and `pytest` before submitting.
