from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Conversation, Message
from tests.fakes import FakeChatModel


def test_chat_creates_conversation_and_persists_messages(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, session_factory = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "你好",
                "user_id": "u1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Fake response: 你好"
    conversation_id = body["conversation_id"]
    assert conversation_id is not None

    async def read_messages() -> tuple[Conversation, list[Message]]:
        async with session_factory() as session:
            conversation = await session.get(Conversation, conversation_id)
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )
            return conversation, list(result.scalars())

    import asyncio

    conversation, messages = asyncio.run(read_messages())
    assert conversation is not None
    assert conversation.user_id == "u1"
    assert [(message.role, message.content) for message in messages] == [
        ("user", "你好"),
        ("assistant", "Fake response: 你好"),
    ]


def test_chat_rejects_unowned_conversation(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, session_factory = api_app

    async def create_conversation() -> int:
        async with session_factory() as session:
            conversation = Conversation(user_id="owner")
            session.add(conversation)
            await session.commit()
            return conversation.id

    import asyncio

    conversation_id = asyncio.run(create_conversation())

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "越权访问",
                "conversation_id": conversation_id,
                "user_id": "other",
            },
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "会话不存在或不可访问"


def test_chat_rejects_missing_user_id(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "你好"},
        )

    assert response.status_code == 422


def test_chat_rejects_empty_message(
    api_app: tuple[object, async_sessionmaker[AsyncSession]],
) -> None:
    app, _ = api_app

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "message": "",
                "user_id": "u1",
            },
        )

    assert response.status_code == 422
