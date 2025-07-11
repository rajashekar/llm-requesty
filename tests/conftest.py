import pytest
import os

REQUESTY_KEY = os.getenv("PYTEST_REQUESTY_KEY", "sk-q6vDn0MfS2GCkAEratyY+m5OIgkmYtj41683OAZMP7s4HJkiLyoaV0TUq8eRjMaBzMxxOKQeOuY2JL/j/qZ17bHCs1kVXI256r5GBZey3wY=")


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization", "x-api-key"],
        "record_mode": "new_episodes",
        "decode_compressed_response": True
    }


@pytest.fixture
def user_path(tmpdir):
    dir = tmpdir / "llm.datasette.io"
    dir.mkdir()
    return dir


@pytest.fixture(autouse=True)
def env_setup(monkeypatch, user_path):
    monkeypatch.setenv("LLM_USER_PATH", str(user_path))
    monkeypatch.setenv("requesty_KEY", REQUESTY_KEY)
    # Remove Lambda Labs key to disable the plugin entirely
    monkeypatch.delenv("LLM_LAMBDALABS_KEY", raising=False)