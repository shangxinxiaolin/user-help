from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.db.checkpointer import open_checkpointer
from app.graph.build import build_graph
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_checkpointer_restores_messages_after_reopening(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "checkpoints.sqlite"

    async with open_checkpointer(str(db_path)) as saver:
        graph = build_graph(FakeChatModel(), checkpointer=saver)
        await graph.ainvoke(
            {"messages": [HumanMessage(content="第一轮")]},
            config={"configurable": {"thread_id": "42"}},
        )

    async with open_checkpointer(str(db_path)) as saver:
        graph = build_graph(FakeChatModel(), checkpointer=saver)
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="第二轮")]},
            config={"configurable": {"thread_id": "42"}},
        )

        messages = result["messages"]
        assert len(messages) == 4
        assert [type(message) for message in messages] == [
            HumanMessage,
            AIMessage,
            HumanMessage,
            AIMessage,
        ]
        assert [message.content for message in messages] == [
            "第一轮",
            "Fake response: 第一轮",
            "第二轮",
            "Fake response: 第二轮",
        ]
