import sqlite3
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.graph.build import build_graph
from tests.fakes import FakeChatModel

def _checkpoint_thread_ids(db_path: str) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT thread_id FROM checkpoints"
        ).fetchall()
    return {row[0] for row in rows}



@pytest.mark.parametrize("endpoint", ["/api/chat", "/api/agent"])
def test_endpoints_use_lifespan_graph(
    endpoint: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "checkpoints.sqlite"

    settings = SimpleNamespace(
        checkpointer_db_path=str(db_path)
    )

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: settings,
    )


    def build_test_graph(model=None, repository=None, checkpointer=None):
        return build_graph(
            model=FakeChatModel(),
            repository=repository,
            checkpointer=checkpointer,
        )

    monkeypatch.setattr(
        main_module,
        "build_graph",
        build_test_graph,
    )

    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.post(
            endpoint,
            json={
                "message": "你好",
                "conversation_id": 42,
                "user_id": "u1",
            },
        )

    assert response.status_code == 200
    assert "42" in _checkpoint_thread_ids(str(db_path))