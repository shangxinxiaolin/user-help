from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import Conversation, Message


class ConversationRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def create_conversation(self, user_id: str) -> int:
        async with self._session_factory() as session:
            conversation = Conversation(user_id=user_id)
            session.add(conversation)
            await session.flush()
            conversation_id = conversation.id
            await session.commit()
            return conversation_id

    async def get_conversation(
        self,
        conversation_id: int,
    ) -> Conversation | None:
        async with self._session_factory() as session:
            return await session.get(Conversation, conversation_id)

    async def get_conversation_for_user(
        self,
        conversation_id: int,
        user_id: str,
    ) -> Conversation | None:
        async with self._session_factory() as session:
            return await session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )

    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str | None = None,
        tool_calls: list | None = None,
        tool_call_id: str | None = None,
    ) -> int:
        async with self._session_factory() as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
            )
            session.add(message)
            await session.flush()
            message_id = message.id
            await session.commit()
            return message_id

    async def list_messages(
        self,
        conversation_id: int,
    ) -> list[Message]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )
            return list(result.scalars())
