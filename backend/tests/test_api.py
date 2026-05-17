"""Tests for the FastAPI API routes."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_endpoint(client):
    resp = client.get("/api/v1/health/readiness")
    assert resp.status_code == 200


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AI Frontend Designer" in resp.json()["message"]


def test_get_nonexistent_session(client):
    resp = client.get("/api/v1/design/session/does-not-exist")
    assert resp.status_code == 404


def test_delete_nonexistent_session(client):
    resp = client.delete("/api/v1/design/session/does-not-exist")
    assert resp.status_code == 404
