from fastapi.testclient import TestClient


def test_liveness_and_readiness_do_not_scan_voc_history(client: TestClient) -> None:
    health = client.get("/healthz")
    readiness = client.get("/readyz")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready"}
