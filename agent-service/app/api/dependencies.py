from fastapi import Request

from app.db.repositories.audit import ToolAuditRepository
from app.db.repositories.conversation import ConversationRepository
from app.db.repositories.flywheel import FlywheelRepository
from app.db.repositories.kb import KnowledgeRepository


def get_conversation_repository(request: Request) -> ConversationRepository:
    return request.app.state.conversation_repository


def get_audit_repository(request: Request) -> ToolAuditRepository | None:
    return getattr(request.app.state, "audit_repository", None)


def get_flywheel_repository(request: Request) -> FlywheelRepository | None:
    return getattr(request.app.state, "flywheel_repository", None)


def get_knowledge_repository(request: Request) -> KnowledgeRepository | None:
    return getattr(request.app.state, "knowledge_repository", None)


def get_business_client(request: Request):
    return getattr(request.app.state, "business_client", None)
