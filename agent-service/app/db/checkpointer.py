from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


@asynccontextmanager
async def open_checkpointer(
    db_path: str,
) -> AsyncGenerator[AsyncSqliteSaver, None]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
        yield saver
