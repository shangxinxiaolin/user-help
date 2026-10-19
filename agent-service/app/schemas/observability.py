from pydantic import BaseModel


class CostReportItem(BaseModel):
    intent: str
    call_count: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float


class MetricsResponse(BaseModel):
    total_turns: int
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost_usd: float
    interrupt_rate: float
