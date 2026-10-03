from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FakeChatModel


client = TestClient(
    create_app(FakeChatModel())
)


def test_agent_returns_complete_response() -> None:
    response = client.post(
        "/api/agent",
        json={
            "message": "你好",
            "conversation_id": 1,
            "user_id": "u1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": 1,
        "answer": "Fake response: 你好",
    }


def test_agent_accepts_request_without_context() -> None:
    response = client.post(
        "/api/agent",
        json={
            "message": "你好",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": None,
        "answer": "Fake response: 你好",
    }


def test_agent_rejects_empty_message() -> None:
    response = client.post(
        "/api/agent",
        json={
            "message": "",
        },
    )

    assert response.status_code == 422
