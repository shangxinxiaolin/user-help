from fastapi.testclient import TestClient


def test_review_queue_apis(api_app):
    app, session_factory = api_app

    with TestClient(app) as client:
        # Trigger unhelpful feedback to generate low-confidence question
        client.post(
            "/api/feedback",
            json={
                "conversation_id": 1,
                "user_id": "u1",
                "question": "耳机怎么降噪",
                "helpful": False,
            },
        )

        # List review queue
        r1 = client.get("/api/review/queue")
        assert r1.status_code == 200
        assert isinstance(r1.json(), list)
