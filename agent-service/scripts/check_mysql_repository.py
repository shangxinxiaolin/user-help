"""Exercise ConversationRepository against the isolated MySQL test database.

Run from agent-service: uv run python -m scripts.check_mysql_repository
"""

import asyncio
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Conversation, Message
from app.db.repositories import ConversationRepository


async def main() -> None:
    url = make_url(get_settings().test_database_url)
    if url.database != "lingxi_agent_test" or url.get_backend_name() != "mysql":
        raise RuntimeError("Refusing to write outside MySQL lingxi_agent_test")

    engine = create_async_engine(url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repository = ConversationRepository(session_factory)
    test_user = f"repository-check-{uuid4().hex}"
    conversation_id: int | None = None

    try:
        async with engine.connect() as connection:
            database = (await connection.execute(text("SELECT DATABASE()"))).scalar_one()
            if database != "lingxi_agent_test":
                raise RuntimeError("Connected to an unexpected database")

        try:
            conversation_id = await repository.create_conversation(test_user)
            conversation = await repository.get_conversation(conversation_id)
            assert conversation is not None
            assert conversation.user_id == test_user
            assert conversation.status == "进行中"

            user_message_id = await repository.append_message(
                conversation_id, "user", content="测试问题"
            )
            assistant_message_id = await repository.append_message(
                conversation_id, "assistant", content="测试回答"
            )
            messages = await repository.list_messages(conversation_id)
            assert [message.id for message in messages] == [
                user_message_id,
                assistant_message_id,
            ]
            assert [message.role for message in messages] == ["user", "assistant"]
            assert [message.content for message in messages] == [
                "测试问题",
                "测试回答",
            ]
            print(f"database={database}")
            print(f"conversation_id={conversation_id}")
            print(f"message_count={len(messages)}")
            print("roles=user,assistant")
        finally:
            if conversation_id is not None:
                # This condition limits cleanup to the row created by this run.
                async with session_factory.begin() as session:
                    owned = await session.scalar(
                        select(Conversation.id).where(
                            Conversation.id == conversation_id,
                            Conversation.user_id == test_user,
                        )
                    )
                    if owned is None:
                        raise RuntimeError("Test conversation ownership changed; refusing cleanup")
                    await session.execute(
                        delete(Message).where(Message.conversation_id == owned)
                    )
                    await session.execute(
                        delete(Conversation).where(
                            Conversation.id == owned,
                            Conversation.user_id == test_user,
                        )
                    )

                async with session_factory() as session:
                    remaining = await session.scalar(
                        select(func.count()).select_from(Conversation).where(
                            Conversation.id == conversation_id,
                            Conversation.user_id == test_user,
                        )
                    )
                    if remaining != 0:
                        raise RuntimeError("Test conversation was not removed")
                print("cleanup=ok")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
