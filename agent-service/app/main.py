from typing import Any

from fastapi import FastAPI

from app.api.agent import create_agent_router
from app.graph.answer import resolve_answer
from app.graph.build import build_graph
from app.graph.runtime import run_turn
from app.schemas.chat import ChatRequest, ChatResponse


def create_app(model: Any | None = None) -> FastAPI:
    app = FastAPI(
        title="Lingxi Agent Service",
        version="0.1.0",
    )

    graph = build_graph(model)

    app.include_router(
        create_agent_router(graph)
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        state = await run_turn(
            graph=graph,
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
        )

        return ChatResponse(
            conversation_id=state.get("conversation_id"),
            answer=resolve_answer(state),
        )

    return app


app = create_app()
