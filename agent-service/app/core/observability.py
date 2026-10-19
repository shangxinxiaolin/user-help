from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class IntentCostStats:
    call_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: float = 0.0


class ObservabilityCollector:
    def __init__(self) -> None:
        self._intent_stats: dict[str, IntentCostStats] = defaultdict(IntentCostStats)
        self._total_turns: int = 0
        self._interrupted_turns: int = 0

    def record_turn(
        self,
        intent: str,
        input_tokens: int,
        output_tokens: int,
        interrupted: bool = False,
    ) -> None:
        self._total_turns += 1
        if interrupted:
            self._interrupted_turns += 1

        stats = self._intent_stats[intent or "其他"]
        stats.call_count += 1
        stats.input_tokens += input_tokens
        stats.output_tokens += output_tokens

        # Estimated cost: e.g. input $0.15/1M ($0.00015/1k), output $0.60/1M ($0.0006/1k)
        cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000.0
        stats.total_cost_usd += round(cost, 6)

    def get_cost_report(self) -> list[dict[str, Any]]:
        report = []
        for intent, stats in sorted(self._intent_stats.items(), key=lambda x: x[1].total_cost_usd, reverse=True):
            report.append({
                "intent": intent,
                "call_count": stats.call_count,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "total_cost_usd": round(stats.total_cost_usd, 4),
            })
        return report

    def get_summary_metrics(self) -> dict[str, Any]:
        total_calls = sum(s.call_count for s in self._intent_stats.values())
        total_in = sum(s.input_tokens for s in self._intent_stats.values())
        total_out = sum(s.output_tokens for s in self._intent_stats.values())
        total_cost = sum(s.total_cost_usd for s in self._intent_stats.values())
        interrupt_rate = (self._interrupted_turns / self._total_turns) if self._total_turns > 0 else 0.0

        return {
            "total_turns": self._total_turns,
            "total_calls": total_calls,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "total_cost_usd": round(total_cost, 4),
            "interrupt_rate": round(interrupt_rate, 4),
        }


collector = ObservabilityCollector()
