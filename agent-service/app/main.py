from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_conversation_repository
from app.api.agent import create_agent_router
from app.core.config import get_settings
from app.db.base import create_engine
from app.db.checkpointer import open_checkpointer
from app.db.repositories import ConversationRepository
from app.graph.answer import resolve_answer
from app.graph.build import build_graph
from app.graph.runtime import ConversationNotFound, run_turn
from app.schemas.chat import ChatRequest, ChatResponse


def create_app(
    model: Any | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        settings = get_settings()
        owned_engine = None
        factory = session_factory

        try:
            if factory is None:
                owned_engine = create_engine(settings.database_url)
                factory = async_sessionmaker(
                    owned_engine,
                    expire_on_commit=False,
                )

            repository = ConversationRepository(factory)
            app.state.conversation_repository = repository

            async with open_checkpointer(
                settings.checkpointer_db_path
            ) as saver:
                app.state.graph = build_graph(
                    model,
                    repository=repository,
                    checkpointer=saver,
                )
                yield
        finally:
            if owned_engine is not None:
                await owned_engine.dispose()

    app = FastAPI(
        title="Lingxi Agent Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(
        create_agent_router()
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        repository: ConversationRepository = Depends(
            get_conversation_repository
        ),
    ) -> ChatResponse:
        if request.user_id is None or not request.user_id.strip():
            raise HTTPException(
                status_code=422,
                detail="user_id is required",
            )

        try:
            state = await run_turn(
                graph=app.state.graph,
                message=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                repository=repository,
            )
        except ConversationNotFound as exc:
            raise HTTPException(
                status_code=404,
                detail="会话不存在或不可访问",
            ) from exc

        return ChatResponse(
            conversation_id=state.get("conversation_id"),
            answer=resolve_answer(state),
        )

    return app


app = create_app()
