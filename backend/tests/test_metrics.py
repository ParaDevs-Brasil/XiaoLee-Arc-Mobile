import importlib

from fastapi.testclient import TestClient

app_module = importlib.import_module("server.app")
from server.metrics import clear_metrics


client = TestClient(app_module.app)


def test_metrics_endpoint_exposes_http_counters():
    clear_metrics()

    response = client.get("/status")
    assert response.status_code == 200

    metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    body = metrics_response.text
    assert 'xiaolee_http_requests_total{method="GET",path="/status",status="200"} 1' in body
    assert "xiaolee_http_request_duration_seconds_avg" in body