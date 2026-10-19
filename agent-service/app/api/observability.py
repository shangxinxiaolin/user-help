from fastapi import APIRouter

from app.core.observability import collector
from app.schemas.observability import CostReportItem, MetricsResponse


def create_observability_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/observability/costs", response_model=list[CostReportItem])
    async def get_cost_report() -> list[CostReportItem]:
        stats = collector.get_cost_report()
        return [
            CostReportItem(
                intent=s["intent"],
                call_count=s["call_count"],
                input_tokens=s["input_tokens"],
                output_tokens=s["output_tokens"],
                total_cost_usd=s["total_cost_usd"],
            )
            for s in stats
        ]

    @router.get("/api/observability/metrics", response_model=MetricsResponse)
    async def get_metrics() -> MetricsResponse:
        metrics = collector.get_summary_metrics()
        return MetricsResponse(
            total_turns=metrics["total_turns"],
            total_calls=metrics["total_calls"],
            total_input_tokens=metrics["total_input_tokens"],
            total_output_tokens=metrics["total_output_tokens"],
            total_cost_usd=metrics["total_cost_usd"],
            interrupt_rate=metrics["interrupt_rate"],
        )

    return router
