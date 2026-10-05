from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.agent import create_agent_router
from app.core.config import get_settings
from app.db.checkpointer import open_checkpointer
from app.graph.answer import resolve_answer
from app.graph.build import build_graph
from app.graph.runtime import run_turn
from app.schemas.chat import ChatRequest, ChatResponse


def create_app(model: Any | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        if model is not None:
            # 现有 FakeChatModel 测试暂沿用无持久化 Graph
            yield
            return

        settings = get_settings()
        async with open_checkpointer(settings.checkpointer_db_path) as saver:
            app.state.graph = build_graph(model, checkpointer=saver)
            yield

    app = FastAPI(
        title="Lingxi Agent Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.graph = build_graph(model)

    app.include_router(
        create_agent_router(app.state.graph)
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        state = await run_turn(
            graph=app.state.graph,
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
