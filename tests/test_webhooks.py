import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from mcp_server.webhooks import app


@pytest.fixture
def client():
    return TestClient(app)


def test_webhook_missing_signature(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")
    response = client.post("/webhook", json={"action": "opened"})
    assert response.status_code == 400
    assert "Missing signature" in response.json()["detail"]


def test_webhook_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")
    response = client.post(
        "/webhook",
        json={"action": "opened"},
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert response.status_code == 401
    assert "Signature mismatch" in response.json()["detail"]


def test_webhook_valid_signature(client, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")
    payload = b'{"action":"opened"}'
    digest = hmac.new(b"test_secret", payload, hashlib.sha256).hexdigest()
    response = client.post(
        "/webhook",
        content=payload,
        headers={
            "X-Hub-Signature-256": f"sha256={digest}",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202


def test_webhook_no_secret_configured(client, monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    response = client.post("/webhook", json={"action": "opened"})
    assert response.status_code == 202
