from typing import Any

from fastapi import APIRouter

from app.graph.answer import resolve_answer
from app.graph.runtime import run_turn
from app.schemas.agent import AgentRequest, AgentResponse


def create_agent_router(graph: Any) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/agent",
        response_model=AgentResponse,
    )
    async def run_agent(
        request: AgentRequest,
    ) -> AgentResponse:
        state = await run_turn(
            graph=graph,
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
        )

        return AgentResponse(
            conversation_id=state.get("conversation_id"),
            answer=resolve_answer(state),
        )

    return router
