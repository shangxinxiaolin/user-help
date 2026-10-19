from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.actions import create_actions_router
from app.api.agent import create_agent_router
from app.api.chat import create_chat_router
from app.api.conversations import create_conversations_router
from app.api.feedback import create_feedback_router
from app.api.kb import create_kb_router
from app.api.observability import create_observability_router
from app.api.review import create_review_router
from app.core.config import get_settings
from app.db.base import create_engine
from app.db.checkpointer import open_checkpointer
from app.db.repositories.audit import ToolAuditRepository
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.flywheel import FlywheelRepository
from app.db.repositories.kb import KnowledgeRepository
from app.graph.build import build_graph
from app.kb.store import default_kb_store


def create_app(
    model: Any | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    full_workflow: bool = False,
    business_client: Any | None = None,
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

            conv_repo = ConversationRepository(factory)
            audit_repo = ToolAuditRepository(factory)
            flywheel_repo = FlywheelRepository(factory)
            kb_repo = KnowledgeRepository(factory)

            app.state.conversation_repository = conv_repo
            app.state.audit_repository = audit_repo
            app.state.flywheel_repository = flywheel_repo
            app.state.knowledge_repository = kb_repo
            app.state.business_client = business_client

            default_kb_store._repository = kb_repo
            await default_kb_store.initialize()

            async with open_checkpointer(
                settings.checkpointer_db_path
            ) as saver:
                app.state.graph = build_graph(
                    model,
                    repository=conv_repo,
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

    # Initialize default graph and state for tests before lifespan
    app.state.graph = build_graph(model)

    # Include all modular routers
    app.include_router(create_chat_router())
    app.include_router(create_agent_router())
    app.include_router(create_actions_router())
    app.include_router(create_conversations_router())
    app.include_router(create_feedback_router())
    app.include_router(create_kb_router())
    app.include_router(create_review_router())
    app.include_router(create_observability_router())

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static_assets")

        @app.get("/", include_in_schema=False)
        async def root():
            return FileResponse(str(static_dir / "index.html"))

    return app


app = create_app()
