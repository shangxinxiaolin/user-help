from fastapi.testclient import TestClient

from app.db.repositories import ConversationRepository
from app.main import create_app
from tests.fakes import FakeChatModel


def test_resume_action_confirmed(api_app):
    app, session_factory = api_app

    with TestClient(app) as client:
        # 1. Start a chat
        r1 = client.post("/api/chat", json={"message": "我要退款", "user_id": "u1"})
        assert r1.status_code == 200
        conv_id = r1.json()["conversation_id"]

        # 2. Resume with confirm
        r2 = client.post(
            "/api/actions/resume",
            json={
                "conversation_id": conv_id,
                "user_id": "u1",
                "confirmed": True,
                "message": "确认申请退款",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "confirmed"
        assert r2.json()["conversation_id"] == conv_id


def test_resume_action_rejects_unowned(api_app):
    app, session_factory = api_app

    with TestClient(app) as client:
        r1 = client.post("/api/chat", json={"message": "你好", "user_id": "u1"})
        conv_id = r1.json()["conversation_id"]

        r2 = client.post(
            "/api/actions/resume",
            json={
                "conversation_id": conv_id,
                "user_id": "u2",
                "confirmed": True,
            },
        )
        assert r2.status_code == 404
