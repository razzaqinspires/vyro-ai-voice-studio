from __future__ import annotations

import hashlib
import re


def demo_namespace(demo_id: str) -> str:
    if not re.fullmatch(r"VYRO-DEMO-[A-Fa-f0-9]{8,40}", demo_id):
        raise ValueError("Demo ID tidak valid")
    return hashlib.sha256(demo_id.upper().encode()).hexdigest()[:24]
