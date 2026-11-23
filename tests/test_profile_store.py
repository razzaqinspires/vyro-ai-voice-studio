import pytest
from vyro_ai_voice_studio.profile_store import resolve_voice_profile


def test_resolves_cli_created_profile_layout(tmp_path):
    folder = tmp_path / "arifi-demo"
    folder.mkdir()
    manifest = folder / "voice_profile.json"
    manifest.write_text("{}", encoding="utf-8")
    assert resolve_voice_profile(tmp_path, "arifi-demo") == manifest.resolve()


def test_supports_legacy_profile_file(tmp_path):
    manifest = tmp_path / "legacy-demo.json"
    manifest.write_text("{}", encoding="utf-8")
    assert resolve_voice_profile(tmp_path, "legacy-demo") == manifest.resolve()


def test_rejects_traversal_profile_id(tmp_path):
    with pytest.raises(ValueError):
        resolve_voice_profile(tmp_path, "..\\outside")
