from langchain_core.messages import HumanMessage, SystemMessage

from app.core.prompts import (
    AGENT_SYSTEM_PROMPT,
    build_chat_prompt,
)


def test_chat_prompt_contains_system_message() -> None:
    prompt = build_chat_prompt()

    messages = prompt.invoke(
        {
            "message": "你好",
        }
    ).messages

    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == AGENT_SYSTEM_PROMPT


def test_chat_prompt_contains_user_message() -> None:
    prompt = build_chat_prompt()

    messages = prompt.invoke(
        {
            "message": "查询订单",
        }
    ).messages

    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "查询订单"


def test_chat_prompt_keeps_message_order() -> None:
    prompt = build_chat_prompt()

    messages = prompt.invoke(
        {
            "message": "你好",
        }
    ).messages

    assert [message.type for message in messages] == [
        "system",
        "human",
    ]
