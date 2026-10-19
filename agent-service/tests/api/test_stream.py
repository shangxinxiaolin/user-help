from fastapi.testclient import TestClient


def test_chat_stream_endpoint(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/chat/stream",
            json={"message": "你好", "user_id": "u1"},
        )
        assert response.status_code == 200
        text = response.text
        assert "data:" in text
        assert "start" in text
        assert "done" in text
