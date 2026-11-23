from __future__ import annotations

import re
from pathlib import Path


def resolve_voice_profile(profile_dir: str | Path, profile_id: str) -> Path | None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", profile_id) or ".." in profile_id:
        raise ValueError("voice_profile_id tidak valid")
    root = Path(profile_dir).expanduser().resolve()
    candidates = (root / profile_id / "voice_profile.json", root / f"{profile_id}.json")
    for candidate in candidates:
        resolved = candidate.resolve()
        if root in resolved.parents and resolved.is_file():
            return resolved
    return None
