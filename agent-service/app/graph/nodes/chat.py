from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.core.llm import get_chat_model
from app.core.prompts import build_chat_prompt
from app.graph.state import ConversationState

ChatNode = Callable[[ConversationState], Awaitable[dict[str, list[AIMessage]]]]


def get_last_human_message(state: ConversationState) -> HumanMessage:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message

    raise ValueError("ConversationState does not contain a HumanMessage")


def make_chat_node(model: Any | None = None) -> ChatNode:
    async def chat_node(state: ConversationState) -> dict[str, list[AIMessage]]:
        human_message = get_last_human_message(state)

        if not isinstance(human_message.content, str):
            raise ValueError("HumanMessage content must be a string")

        prompt_value = build_chat_prompt().invoke(
            {"message": human_message.content}
        )
        chat_model = (
            model
            if model is not None
            else get_chat_model(streaming=True)
        )
        response = await chat_model.ainvoke(prompt_value)

        if not isinstance(response, AIMessage):
            raise TypeError("Chat model must return an AIMessage")

        return {"messages": [response]}

    return chat_node
