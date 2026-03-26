from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError, URLError


SKILL_PATH = Path(__file__).resolve().parents[2] / "skills/github-analyzer/main.py"
MODULE_NAME = "github_analyzer_main_test"


def _load_module():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SKILL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_github_analyzer_success_and_token_header(monkeypatch):
    module = _load_module()
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

    captured_headers: list[dict[str, str]] = []

    def fake_urlopen(req, timeout=5):
        captured_headers.append(dict(req.header_items()))
        url = req.full_url
        if url.endswith("/languages"):
            return _FakeResponse({"Python": 1234})
        return _FakeResponse({"stargazers_count": 10, "forks_count": 2, "open_issues_count": 1})

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    skill = module.SkillEntry()
    result = json.loads(skill.execute({"repo": "owner/repo"}))

    assert result["status"] == "success"
    assert result["language_distribution"]["Python"] == 1234
    assert result["stars"] == 10
    assert any("authorization" in {k.lower() for k in headers.keys()} for headers in captured_headers)


def test_github_analyzer_rate_limit_error(monkeypatch):
    module = _load_module()

    def fake_urlopen(req, timeout=5):
        raise HTTPError(req.full_url, 403, "API rate limit exceeded for 1.2.3.4", hdrs=None, fp=None)

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    skill = module.SkillEntry()
    result = json.loads(skill.execute({"repo": "owner/repo"}))

    assert result["status"] == "error"
    assert result["error_type"] == "rate_limit"
    assert result["http_status"] == 403
    assert result["retryable"] is True
    assert "GITHUB_TOKEN" in result["suggestion"]


def test_github_analyzer_network_error(monkeypatch):
    module = _load_module()

    def fake_urlopen(req, timeout=5):
        raise URLError("temporary failure in name resolution")

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    skill = module.SkillEntry()
    result = json.loads(skill.execute({"repo": "owner/repo"}))

    assert result["status"] == "error"
    assert result["error_type"] == "network_error"
    assert result["retryable"] is True
