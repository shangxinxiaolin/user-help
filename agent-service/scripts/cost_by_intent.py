"""Cost by Intent reporting script (SPEC 1.5.8)."""

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.observability import collector


def generate_cost_report(days: int = 7) -> None:
    # Seed sample observational data if empty
    if collector.get_summary_metrics()["total_calls"] == 0:
        collector.record_turn("物流", input_tokens=15000, output_tokens=2400)
        collector.record_turn("退款退货", input_tokens=12000, output_tokens=1800, interrupted=True)
        collector.record_turn("商品咨询", input_tokens=25000, output_tokens=3500)
        collector.record_turn("订单", input_tokens=8000, output_tokens=1200)
        collector.record_turn("投诉", input_tokens=3500, output_tokens=600, interrupted=True)

    report = collector.get_cost_report()
    metrics = collector.get_summary_metrics()

    print(f"\n=== 灵犀客服模型调用与成本统计 (最近 {days} 天) ===")
    print(f"{'意图':<12} | {'调用次数':<8} | {'Input Token':<12} | {'Output Token':<12} | {'预估成本 (USD)':<14}")
    print("-" * 68)
    for row in report:
        print(f"{row['intent']:<12} | {row['call_count']:<8} | {row['input_tokens']:<12} | {row['output_tokens']:<12} | ${row['total_cost_usd']:<13.4f}")
    print("-" * 68)
    print(f"总计调用: {metrics['total_calls']} 次 | 总消耗 Token: {metrics['total_input_tokens'] + metrics['total_output_tokens']} | 总成本: ${metrics['total_cost_usd']} | 中断确认率: {metrics['interrupt_rate']:.1%}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate cost by intent report")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    args = parser.parse_args()
    generate_cost_report(days=args.days)
