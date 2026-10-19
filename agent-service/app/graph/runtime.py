import json
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.state import ConversationState


class ConversationNotFound(Exception):
    """会话不存在，或不属于当前用户。"""


async def run_turn(
    graph: Any,
    message: str,
    conversation_id: int | None = None,
    user_id: str | None = None,
    repository: ConversationRepository | None = None,
    action_confirmed: bool = False,
    trace_id: str | None = None,
) -> ConversationState:
    ensured_id = conversation_id
    if repository is not None:
        if user_id is None or not user_id.strip():
            raise ValueError("user_id is required")

        ensured_id = await _ensure_conversation(
            repository=repository,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        await repository.append_message(
            conversation_id=ensured_id,
            role="user",
            content=message,
        )

    initial_state: ConversationState = {
        "messages": [
            HumanMessage(content=message)
        ],
        "conversation_id": ensured_id,
        "user_id": user_id,
        "action_confirmed": action_confirmed,
    }

    config = {}
    if ensured_id is not None:
        config["configurable"] = {"thread_id": str(ensured_id)}
    if trace_id:
        config["metadata"] = {"trace_id": trace_id}

    if not config:
        return await graph.ainvoke(initial_state)

    return await graph.ainvoke(initial_state, config=config)


async def resume_turn(
    graph: Any,
    conversation_id: int,
    user_id: str,
    confirmed: bool,
    repository: ConversationRepository | None = None,
    message: str | None = None,
) -> ConversationState:
    if repository is not None:
        conv = await repository.get_conversation_for_user(conversation_id, user_id)
        if conv is None:
            raise ConversationNotFound()

    confirm_msg = message or ("确认提交" if confirmed else "取消操作")
    return await run_turn(
        graph=graph,
        message=confirm_msg,
        conversation_id=conversation_id,
        user_id=user_id,
        repository=repository,
        action_confirmed=confirmed,
    )


async def stream_turn(
    graph: Any,
    message: str,
    conversation_id: int | None = None,
    user_id: str | None = None,
    repository: ConversationRepository | None = None,
    action_confirmed: bool = False,
    trace_id: str | None = None,
) -> AsyncGenerator[str, None]:
    ensured_id = conversation_id
    if repository is not None:
        if user_id is None or not user_id.strip():
            raise ValueError("user_id is required")

        ensured_id = await _ensure_conversation(
            repository=repository,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        await repository.append_message(
            conversation_id=ensured_id,
            role="user",
            content=message,
        )

    initial_state: ConversationState = {
        "messages": [
            HumanMessage(content=message)
        ],
        "conversation_id": ensured_id,
        "user_id": user_id,
        "action_confirmed": action_confirmed,
    }

    config = {}
    if ensured_id is not None:
        config["configurable"] = {"thread_id": str(ensured_id)}

    # Send SSE start event
    yield f"data: {json.dumps({'event': 'start', 'conversation_id': ensured_id}, ensure_ascii=False)}\n\n"

    try:
        final_state: dict = {}
        # Stream events or ainvoke
        if hasattr(graph, "astream_events"):
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                kind = event.get("event")
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    content = getattr(chunk, "content", "")
                    if content:
                        yield f"data: {json.dumps({'event': 'token', 'delta': content}, ensure_ascii=False)}\n\n"
                elif kind == "on_tool_start":
                    tool_name = event.get("name")
                    yield f"data: {json.dumps({'event': 'tool_start', 'tool': tool_name}, ensure_ascii=False)}\n\n"

            # Finally get state
            final_state = await graph.ainvoke(initial_state, config=config) if not final_state else final_state
        else:
            final_state = await graph.ainvoke(initial_state, config=config)
            ans = resolve_answer(final_state)
            yield f"data: {json.dumps({'event': 'token', 'delta': ans}, ensure_ascii=False)}\n\n"

        ans = resolve_answer(final_state)
        pending = final_state.get("pending_action")
        citations = final_state.get("citations", [])

        if pending:
            yield f"data: {json.dumps({'event': 'action_required', 'action': pending}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'event': 'done', 'answer': ans, 'citations': citations, 'conversation_id': ensured_id}, ensure_ascii=False)}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'event': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"


async def _ensure_conversation(
    repository: ConversationRepository,
    user_id: str,
    conversation_id: int | None,
) -> int:
    if conversation_id is None:
        return await repository.create_conversation(user_id)

    conversation = await repository.get_conversation_for_user(
        conversation_id,
        user_id,
    )
    if conversation is None:
        raise ConversationNotFound()

    return conversation.id
