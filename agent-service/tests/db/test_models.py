from app.db.base import Base
from app.db.models import Conversation, Message


def test_agent_db_registers_conversation_and_message_tables() -> None:
    assert set(Base.metadata.tables) == {
        "conversations",
        "messages",
    }


def test_conversation_columns_match_contract() -> None:
    table = Conversation.__table__

    assert set(table.columns.keys()) == {
        "id",
        "user_id",
        "status",
        "summary",
        "summary_upto_msg_id",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert table.c.user_id.nullable is False
    assert table.c.status.server_default.arg == "进行中"


def test_message_columns_and_foreign_key_match_contract() -> None:
    table = Message.__table__

    assert set(table.columns.keys()) == {
        "id",
        "conversation_id",
        "role",
        "content",
        "tool_calls",
        "tool_call_id",
        "created_at",
    }
    assert table.c.id.primary_key is True
    assert table.c.conversation_id.nullable is False
    assert {
        str(foreign_key.column)
        for foreign_key in table.c.conversation_id.foreign_keys
    } == {"conversations.id"}
