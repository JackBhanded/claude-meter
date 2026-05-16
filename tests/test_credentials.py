import json

from claude_usage_widget import credentials


def test_parse_valid_credentials_file(tmp_path):
    f = tmp_path / ".credentials.json"
    f.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-test",
            "refreshToken": "sk-ant-ort01-test",
            "expiresAt": 99999999999999,
            "scopes": ["user:inference"],
        },
    }))
    cred = credentials._parse_claude_credentials_file(f, source=str(f))
    assert cred is not None
    assert cred.kind == "oauth"
    assert cred.token == "sk-ant-oat01-test"
    assert cred.is_expired is False


def test_parse_missing_oauth(tmp_path):
    f = tmp_path / ".credentials.json"
    f.write_text("{}")
    assert credentials._parse_claude_credentials_file(f, source=str(f)) is None


def test_parse_corrupt_file(tmp_path):
    f = tmp_path / ".credentials.json"
    f.write_text("not json at all")
    assert credentials._parse_claude_credentials_file(f, source=str(f)) is None


def test_env_var_fallback(monkeypatch):
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api01-test")
    cred = credentials.discover()
    assert cred is not None
    assert cred.kind == "api_key"
    assert cred.token == "sk-ant-api01-test"


def test_expired_oauth_detected(tmp_path):
    f = tmp_path / ".credentials.json"
    f.write_text(json.dumps({
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-expired",
            "expiresAt": 0,
        },
    }))
    cred = credentials._parse_claude_credentials_file(f, source=str(f))
    assert cred is not None
    assert cred.is_expired is True
