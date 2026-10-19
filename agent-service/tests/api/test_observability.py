from fastapi.testclient import TestClient


def test_observability_endpoints(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        # Chat once
        client.post("/api/chat", json={"message": "你好", "user_id": "u1"})

        # Get cost report
        r1 = client.get("/api/observability/costs")
        assert r1.status_code == 200
        assert isinstance(r1.json(), list)

        # Get metrics
        r2 = client.get("/api/observability/metrics")
        assert r2.status_code == 200
        assert "total_turns" in r2.json()
