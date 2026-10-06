from fastapi import Request

from app.db.repositories import ConversationRepository

def get_conversation_repository(
    request: Request,
) -> ConversationRepository:
    return request.app.state.conversation_repository