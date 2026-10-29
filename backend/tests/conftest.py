import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
SAMPLES = ROOT / "data" / "sample_transcripts"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A fresh app per test: SQLite + temp Chroma dir + offline embedder/LLM."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("MIN_SIMILARITY", "")

    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker
    from app.services.embedder import get_embedder
    from app.services.llm import get_llm
    from app.services.vector_store import get_vector_store

    for fn in (get_settings, get_engine, get_sessionmaker, get_embedder, get_llm, get_vector_store):
        fn.cache_clear()

    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as c:
        response = c.post(
            "/api/auth/signup",
            json={"username": "Test User", "email": "test@example.com", "password": "test-password-123"},
        )
        assert response.status_code == 201, response.text
        c.auth_token = response.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {c.auth_token}"
        yield c


@pytest.fixture()
def loaded(client):
    """Client with all six sample meetings ingested."""
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    ids = {}
    for m in manifest:
        r = client.post(
            "/api/meetings",
            files={"file": (m["file"], (SAMPLES / m["file"]).read_bytes())},
            data={"title": m["title"], "meeting_date": m["date"], "platform": m["platform"]},
        )
        assert r.status_code == 201, r.text
        ids[m["title"]] = r.json()["id"]
    client.ids = ids
    return client
