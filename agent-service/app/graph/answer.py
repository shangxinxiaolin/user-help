from langchain_core.messages import AIMessage

from app.graph.state import ConversationState


def resolve_answer(state: ConversationState) -> str:
    if state.get("answer"):
        return state["answer"]

    for message in reversed(
        state.get("messages", [])
    ):
        if not isinstance(message, AIMessage):
            continue

        content = message.content

        if isinstance(content, str):
            return content

        return "".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )

    return ""