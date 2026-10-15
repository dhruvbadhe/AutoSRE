from types import SimpleNamespace

import httpx
import pytest
from typer.testing import CliRunner

from app import cli

runner = CliRunner()

API_RESPONSE = {
    "id": "inc-42",
    "service": "auth-service",
    "severity": "CRITICAL",
    "status": "RESOLVED",
    "hypothesis": "JVM heap leak in the session cache",
    "proposed_fix": "kubectl rollout restart deployment/auth-service",
    "fix_confidence": 0.9,
    "post_mortem_draft": "",
    "audit_logs": [],
}


class FakeApi:
    """Stands in for httpx.Client: records posts, then returns a 201 or raises like a server that is not running."""

    def __init__(self, error=None):
        self.error = error
        self.posts = []

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json):
        self.posts.append((url, json))
        if self.error:
            raise self.error
        return SimpleNamespace(status_code=201, json=lambda: API_RESPONSE)


@pytest.fixture
def api_up(monkeypatch):
    api = FakeApi()
    monkeypatch.setattr(cli.httpx, "Client", api)
    return api


@pytest.fixture
def api_down(monkeypatch):
    api = FakeApi(error=httpx.ConnectError("[Errno 61] Connection refused"))
    monkeypatch.setattr(cli.httpx, "Client", api)
    return api


def test_help_lists_commands():
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    for command in ("triage", "history", "benchmark"):
        assert command in result.output


def test_piped_stdin_becomes_alert_and_logs(api_up):
    piped = "CRITICAL: auth-service OOMKilled\njava.lang.OutOfMemoryError: Java heap space\n\n"

    result = runner.invoke(cli.app, ["triage", "--api-url", "http://api.test"], input=piped)

    assert result.exit_code == 0, result.output
    assert api_up.posts == [(
        "http://api.test/api/incidents/triage",
        {
            "raw_alert": "CRITICAL: auth-service OOMKilled",
            "raw_logs": ["CRITICAL: auth-service OOMKilled", "java.lang.OutOfMemoryError: Java heap space"],
        },
    )]
    assert "inc-42" in result.output


def test_no_alert_exits_nonzero_with_usage_hint(api_up):
    result = runner.invoke(cli.app, ["triage"], input="")

    assert result.exit_code == 1
    assert "No alert specified" in result.output
    assert api_up.posts == []


def test_api_down_falls_back_to_local_runtime(api_down):
    result = runner.invoke(cli.app, ["triage", "--alert", "CRITICAL: auth-service pod OOMKilled"])

    assert result.exit_code == 0, result.output
    assert len(api_down.posts) == 1
    assert "Incident Resolution Summary" in result.output
    assert "RESOLVED" in result.output


def test_api_down_and_local_runtime_failing_gives_clear_error(api_down, monkeypatch):
    def broken_runtime(alert, logs):
        raise RuntimeError("GEMINI_API_KEY is not set")

    monkeypatch.setattr(cli, "execute_triage_direct", broken_runtime)

    result = runner.invoke(cli.app, ["triage", "--alert", "CRITICAL: auth-service pod OOMKilled"])

    assert result.exit_code == 1
    assert "Triage execution failed: GEMINI_API_KEY is not set" in result.output
