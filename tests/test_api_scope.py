import pytest
from vyro_ai_voice_studio.demo_scope import demo_namespace


def test_demo_namespace_hashes_id():
    value = demo_namespace("VYRO-DEMO-1234ABCD")
    assert len(value) == 24
    assert value != "VYRO-DEMO-1234ABCD"


def test_demo_namespace_rejects_invalid_id():
    with pytest.raises(ValueError):
        demo_namespace("not-a-demo")
