from vyro_ai_voice_studio.text_chunker import normalize_speech_text, split_text


def test_splitter_keeps_all_words_and_punctuation():
    text = "Kalimat pertama. Kalimat kedua! Ini paragraf yang cukup panjang untuk menguji pemotongan tanpa memutus kata."
    clean = normalize_speech_text(text)
    chunks = split_text(text, max_chars=30)
    assert " ".join(chunks) == clean
    assert all(len(chunk) <= 30 for chunk in chunks)


def test_splitter_handles_empty_text():
    assert split_text("  \n ") == []


def test_splitter_does_not_split_words():
    chunks = split_text("VYRO MEDIA membuat konten kreatif untuk audiens Indonesia.", max_chars=24)
    assert all(" " in c or len(c) <= 24 for c in chunks)
    assert " ".join(chunks) == "VYRO MEDIA membuat konten kreatif untuk audiens Indonesia."
