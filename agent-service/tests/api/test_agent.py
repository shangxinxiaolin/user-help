from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fastapi.testclient import TestClient


def test_agent_returns_complete_response(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/agent",
            json={
                "message": "你好",
                "user_id": "u1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] is not None
    assert body["answer"] == "Fake response: 你好"


def test_agent_rejects_missing_user_id(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/agent",
            json={"message": "你好"},
        )

    assert response.status_code == 422


def test_agent_rejects_empty_message(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/agent",
            json={
                "message": "",
                "user_id": "u1",
            },
        )

    assert response.status_code == 422
