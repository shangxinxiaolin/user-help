import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatResponse


def test_chat_request_accepts_valid_message() -> None:
    request = ChatRequest(message="你好")

    assert request.message == "你好"
    assert request.conversation_id is None
    assert request.user_id is None


def test_chat_request_accepts_context_fields() -> None:
    request = ChatRequest(
        message="查询订单",
        conversation_id=1,
        user_id="u1",
    )

    assert request.message == "查询订单"
    assert request.conversation_id == 1
    assert request.user_id == "u1"


def test_chat_request_rejects_empty_message() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_response_requires_answer() -> None:
    response = ChatResponse(
        conversation_id=1,
        answer="你好，我是灵犀客服。",
    )

    assert response.conversation_id == 1
    assert response.answer == "你好，我是灵犀客服。"
