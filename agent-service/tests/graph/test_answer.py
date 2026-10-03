from langchain_core.messages import AIMessage, HumanMessage

from app.graph.answer import resolve_answer


def test_resolve_answer_returns_last_ai_message() -> None:
    state = {
        "messages": [
            HumanMessage(content="你好"),
            AIMessage(content="你好，有什么可以帮你？"),
            HumanMessage(content="查询订单"),
            AIMessage(content="请提供订单号"),
        ]
    }

    assert resolve_answer(state) == "请提供订单号"


def test_resolve_answer_returns_empty_string_without_ai_message() -> None:
    state = {"messages": [HumanMessage(content="你好")]}

    assert resolve_answer(state) == ""
