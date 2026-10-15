import json
import os
import socket
import tempfile
import zlib
from types import SimpleNamespace

import pytest

# Must run before any app import: Settings() reads these at import time, and tests
# must never use a real key, the local incidents.db or the local chroma_db.
_tmp = tempfile.mkdtemp(prefix="autosre-tests-")
os.environ["GEMINI_API_KEY"] = "test-key-not-real"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CHROMA_DB_PATH"] = os.path.join(_tmp, "chroma")
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from app.services import llm  # noqa: E402
from app.services.embedder import embedder  # noqa: E402
from app.graph.nodes import rewriter  # noqa: E402

_real_connect = socket.socket.connect


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def guard(sock, address, *args, **kwargs):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(f"Network access attempted in tests: {address}")
        return _real_connect(sock, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard)


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    def embed_documents(texts):
        # Hashed bag-of-words: deterministic, and texts sharing words land close together.
        vectors = []
        for text in texts:
            vec = [0.0] * 64
            vec[0] = 1e-3
            for token in text.lower().split():
                vec[zlib.crc32(token.encode()) % 64] += 1.0
            vectors.append(vec)
        return vectors

    monkeypatch.setattr(embedder, "embed_documents", embed_documents)


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Canned Gemini replies keyed by node. Tests change a reply by assigning to the returned dict."""
    replies = {
        "grader": "SUFFICIENT",
        "fix": json.dumps({"proposed_fix": "kubectl rollout restart deployment/auth-service", "confidence": 0.9}),
        "rewriter": "auth-service OOMKilled java heap",
        "default": "Root cause: JVM heap exhausted by a memory leak in auth-service.",
    }

    def generate_content(prompt):
        if "SRE Audit Grader" in prompt:
            key = "grader"
        elif "Lead Infrastructure Engineer" in prompt:
            key = "fix"
        elif "Search Optimization Specialist" in prompt:
            key = "rewriter"
        else:
            key = "default"
        return SimpleNamespace(text=replies[key])

    monkeypatch.setattr(llm, "model", SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(rewriter, "DDGS", lambda: SimpleNamespace(text=lambda query, max_results: []))
    return replies
