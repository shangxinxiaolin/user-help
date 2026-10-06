from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from fastapi import FastAPI

import app.main as main_module
from app.db.base import Base
from tests.fakes import FakeChatModel


@pytest_asyncio.fixture
async def api_app(
    tmp_path: Path,
    monkeypatch,
) -> AsyncIterator[tuple[FastAPI, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "agent-api.sqlite"
    checkpoint_path = tmp_path / "checkpoints.sqlite"
    engine: AsyncEngine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}"
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: SimpleNamespace(
            checkpointer_db_path=str(checkpoint_path),
            database_url=f"sqlite+aiosqlite:///{database_path}",
        ),
    )

    app = main_module.create_app(
        model=FakeChatModel(),
        session_factory=session_factory,
    )

    try:
        yield app, session_factory
    finally:
        await engine.dispose()
