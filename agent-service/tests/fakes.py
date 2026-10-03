from typing import Any

from langchain_core.messages import AIMessage


class FakeChatModel:
    async def ainvoke(self, messages: Any) -> AIMessage:
        user_message = messages.messages[-1]
        return AIMessage(content=f"Fake response: {user_message.content}")
