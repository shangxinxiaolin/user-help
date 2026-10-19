from fastapi.testclient import TestClient


def test_submit_feedback(api_app):
    app, _ = api_app

    with TestClient(app) as client:
        # 1. Helpful feedback
        r1 = client.post(
            "/api/feedback",
            json={
                "conversation_id": 1,
                "user_id": "u1",
                "question": "运费怎么算",
                "helpful": True,
            },
        )
        assert r1.status_code == 200
        assert r1.json()["success"] is True

        # 2. Unhelpful feedback
        r2 = client.post(
            "/api/feedback",
            json={
                "conversation_id": 1,
                "user_id": "u1",
                "question": "耳机怎么连两台手机",
                "helpful": False,
                "reason": "回答不明确",
            },
        )
        assert r2.status_code == 200
