from __future__ import annotations

import re


def normalize_speech_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("text harus berupa string")
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def split_text(text: str, max_chars: int = 360) -> list[str]:
    """Split into readable chunks on sentence/word boundaries, keeping all words and punctuation."""
    clean = normalize_speech_text(text)
    if not clean:
        return []
    if max_chars < 20:
        raise ValueError("max_chars minimal 20")
    if len(clean) <= max_chars:
        return [clean]

    sentences = re.split(r"(?<=[.!?;:。！？])\s+", clean)
    chunks: list[str] = []
    current = ""

    def push(value: str) -> None:
        if value.strip():
            chunks.append(value.strip())

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            push(current)
            current = ""
        if len(sentence) <= max_chars:
            current = sentence
            continue
        # Word-boundary fallback for one exceptionally long sentence.
        words = sentence.split()
        piece = ""
        for word in words:
            candidate = f"{piece} {word}".strip()
            if len(candidate) > max_chars and piece:
                push(piece)
                piece = word
            else:
                piece = candidate
        current = piece
    if current:
        push(current)
    return chunks
