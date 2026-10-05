from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.db.repositories import ConversationRepository
from app.graph.build import build_graph
from app.graph.runtime import ConversationNotFound, _ensure_conversation, run_turn
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_run_turn_preserves_context() -> None:
    graph = build_graph(FakeChatModel())

    result = await run_turn(
        graph=graph,
        message="你好",
        conversation_id=1,
        user_id="u1",
    )

    assert len(result["messages"]) == 2

    assert isinstance(
        result["messages"][0],
        HumanMessage,
    )

    assert isinstance(
        result["messages"][1],
        AIMessage,
    )

    assert result["messages"][0].content == "你好"
    assert (
        result["messages"][1].content
        == "Fake response: 你好"
    )

    assert result["conversation_id"] == 1
    assert result["user_id"] == "u1"


@pytest.mark.asyncio
async def test_run_turn_uses_ensured_conversation_id() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    repository.create_conversation.return_value = 42
    graph = build_graph(FakeChatModel())

    result = await run_turn(
        graph=graph,
        repository=repository,
        message="你好",
        user_id="u1",
    )

    assert result["conversation_id"] == 42
    repository.create_conversation.assert_awaited_once_with("u1")
    repository.append_message.assert_awaited_once_with(
        conversation_id=42,
        role="user",
        content="你好",
    )


@pytest.mark.asyncio
async def test_run_turn_rejects_unowned_conversation_before_graph() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    repository.get_conversation_for_user.return_value = None
    graph = AsyncMock()

    with pytest.raises(ConversationNotFound):
        await run_turn(
            graph=graph,
            repository=repository,
            message="你好",
            conversation_id=42,
            user_id="u1",
        )

    graph.ainvoke.assert_not_awaited()
    repository.append_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_conversation_creates_new_conversation() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    repository.create_conversation.return_value = 42

    conversation_id = await _ensure_conversation(
        repository=repository,
        user_id="u1",
        conversation_id=None,
    )

    assert conversation_id == 42
    repository.create_conversation.assert_awaited_once_with("u1")
    repository.get_conversation_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_conversation_accepts_owned_conversation() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    repository.get_conversation_for_user.return_value = SimpleNamespace(id=42)

    conversation_id = await _ensure_conversation(
        repository=repository,
        user_id="u1",
        conversation_id=42,
    )

    assert conversation_id == 42
    repository.get_conversation_for_user.assert_awaited_once_with(42, "u1")
    repository.create_conversation.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_conversation_rejects_missing_or_unowned_conversation() -> None:
    repository = AsyncMock(spec=ConversationRepository)
    repository.get_conversation_for_user.return_value = None

    with pytest.raises(ConversationNotFound):
        await _ensure_conversation(
            repository=repository,
            user_id="u1",
            conversation_id=42,
        )

    repository.get_conversation_for_user.assert_awaited_once_with(42, "u1")
    repository.create_conversation.assert_not_awaited()
