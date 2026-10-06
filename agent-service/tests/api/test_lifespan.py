import asyncio
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.main as main_module
from app.db.base import Base
from app.graph.build import build_graph
from tests.fakes import FakeChatModel


def _checkpoint_thread_ids(db_path: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT DISTINCT thread_id FROM checkpoints"
        ).fetchall()
    return {row[0] for row in rows}


@pytest.mark.parametrize("endpoint", ["/api/chat", "/api/agent"])
def test_endpoints_use_lifespan_graph(
    endpoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpoint_path = tmp_path / "checkpoints.sqlite"
    database_path = tmp_path / "agent-api.sqlite"
    engine: AsyncEngine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}"
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    settings = type(
        "TestSettings",
        (),
        {
            "checkpointer_db_path": str(checkpoint_path),
            "database_url": "sqlite+aiosqlite:///unused.sqlite",
        },
    )()
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)

    def build_test_graph(model=None, repository=None, checkpointer=None):
        return build_graph(
            model=FakeChatModel(),
            repository=repository,
            checkpointer=checkpointer,
        )

    monkeypatch.setattr(main_module, "build_graph", build_test_graph)

    app = main_module.create_app(session_factory=session_factory)

    try:
        with TestClient(app) as client:
            response = client.post(
                endpoint,
                json={
                    "message": "你好",
                    "user_id": "u1",
                },
            )

        assert response.status_code == 200
        conversation_id = response.json()["conversation_id"]
        assert conversation_id is not None
        assert str(conversation_id) in _checkpoint_thread_ids(
            str(checkpoint_path)
        )
    finally:
        asyncio.run(engine.dispose())
