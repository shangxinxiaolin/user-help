from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.repositories import ConversationRepository


@pytest_asyncio.fixture
async def repository(
    tmp_path: Path,
) -> AsyncIterator[ConversationRepository]:
    database_path = tmp_path / "agent-test.sqlite"
    engine: AsyncEngine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}"
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield ConversationRepository(session_factory)

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_conversation(
    repository: ConversationRepository,
) -> None:
    conversation_id = await repository.create_conversation("u1")

    conversation = await repository.get_conversation(conversation_id)

    assert conversation is not None
    assert conversation.id == conversation_id
    assert conversation.user_id == "u1"
    assert conversation.status == "进行中"
    assert conversation.summary is None
    assert conversation.summary_upto_msg_id is None


@pytest.mark.asyncio
async def test_append_and_list_messages_in_order(
    repository: ConversationRepository,
) -> None:
    conversation_id = await repository.create_conversation("u1")

    user_message_id = await repository.append_message(
        conversation_id=conversation_id,
        role="user",
        content="你好",
    )
    assistant_message_id = await repository.append_message(
        conversation_id=conversation_id,
        role="assistant",
        content="你好，有什么可以帮你？",
        tool_calls=[{"name": "query_order", "args": {"order_id": "1001"}}],
    )

    messages = await repository.list_messages(conversation_id)

    assert [message.id for message in messages] == [
        user_message_id,
        assistant_message_id,
    ]
    assert [message.role for message in messages] == ["user", "assistant"]
    assert [message.content for message in messages] == [
        "你好",
        "你好，有什么可以帮你？",
    ]
    assert messages[1].tool_calls == [
        {"name": "query_order", "args": {"order_id": "1001"}}
    ]
