"""HTTP integration tests for the clinical endpoint and legacy access controls."""
from fastapi.testclient import TestClient
from agents.api import app

client = TestClient(app)


def test_mipi_api_calculates_valid_score():
    res = client.post("/api/mipi", json={
        "age": 60, "ecog": 0, "wbc": 10, "ldh_ratio": 1, "ki67": 30
    })
    assert res.status_code == 200
    data = res.json()
    assert data["classification"] == "Intermediate"
    assert data["simplified_score"] == 6
    assert "biological_score" in data


def test_mipi_api_rejects_nonpositive_wbc():
    res = client.post("/api/mipi", json={
        "age": 60, "ecog": 0, "wbc": 0, "ldh_ratio": 1
    })
    assert res.status_code == 422


def test_legacy_endpoints_not_open_by_default(monkeypatch):
    monkeypatch.delenv("AUDIT_API_TOKEN", raising=False)
    assert client.get("/api/audit/logs").status_code == 403
    assert client.post("/api/chat", json={"query": "ping"}).status_code == 403
    res = client.post("/api/audit", json={
        "task_id": "TASK", "target_identifier": "SPECIMEN",
        "primary_metric": 12, "secondary_metric": 1
    })
    assert res.status_code == 403


def test_legacy_token_check(monkeypatch):
    monkeypatch.setenv("AUDIT_API_TOKEN", "test-token-only")
    assert client.get("/api/audit/logs", headers={"X-Audit-Token": "bad"}).status_code == 403
    assert client.get("/api/audit/logs", headers={"X-Audit-Token": "test-token-only"}).status_code == 200
