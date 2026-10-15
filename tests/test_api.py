from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "orchestrator" in data

def test_metrics_endpoint():
    response = client.get("/api/incidents/metrics")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"total_incidents", "resolved_count", "escalated_count", "open_count", "mttr_seconds"}
    assert data.get("mttr_seconds") >= 0.0

def test_list_incidents_endpoint():
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)