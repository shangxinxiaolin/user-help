import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.graph.build import build_workflow_graph
from app.graph.runtime import resume_turn, stream_turn
from tests.fakes import FakeChatModel


@pytest.mark.asyncio
async def test_build_workflow_graph_execution():
    graph = build_workflow_graph(model=FakeChatModel())
    res = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="你好")],
            "user_id": "u1",
        }
    )
    assert len(res["messages"]) >= 2
    last_msg = res["messages"][-1]
    assert isinstance(last_msg, AIMessage)


@pytest.mark.asyncio
async def test_workflow_complaint_escalation():
    graph = build_workflow_graph(model=FakeChatModel())
    res = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="我要投诉你们态度太差了！")],
            "user_id": "u1",
        }
    )
    ans = res.get("answer") or res["messages"][-1].content
    assert "非常抱歉" in ans
    assert "投诉" in ans or "专员" in ans


@pytest.mark.asyncio
async def test_stream_turn():
    graph = build_workflow_graph(model=FakeChatModel())
    events = []
    async for chunk in stream_turn(graph=graph, message="你好", user_id="u1"):
        events.append(chunk)

    assert len(events) >= 2
    assert any("start" in e for e in events)
    assert any("done" in e for e in events)
