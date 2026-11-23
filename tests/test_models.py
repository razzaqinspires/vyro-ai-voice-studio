import pytest
from pydantic import ValidationError
from vyro_ai_voice_studio.models import VoiceAuthorization, VoiceRequest


def test_voice_job_requires_consent_confirmation():
    with pytest.raises(ValidationError):
        VoiceRequest(content_id="vyro-demo-001", text="Ini teks narasi yang cukup panjang.",
                     voice_profile_path="profile.json", consent_confirmation=False)


def test_voice_authorization_requires_rights():
    with pytest.raises(ValidationError):
        VoiceAuthorization(rights_confirmed=False, subject_relationship="self",
                           consent_record_id="consent-1234", consent_scope="Use for own voice", consent_date="2026-01-01")


def test_authorized_profile_attestation_validates():
    item=VoiceAuthorization(rights_confirmed=True, subject_relationship="self",
      consent_record_id="consent-1234", consent_scope="Use my voice for speech synthesis", consent_date="2026-01-01")
    assert item.rights_confirmed is True


def test_voice_request_rejects_path_traversal():
    with pytest.raises(ValidationError):
        VoiceRequest(content_id="../oops", text="Ini adalah narasi yang cukup panjang.",
                     voice_profile_path="profile.json", consent_confirmation=True)
