from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # Chinese character ~1 token; English words ~1.3 tokens
    return len(text)


def truncate_middle_message(msg: AnyMessage, max_chars: int = 50) -> AnyMessage:
    content = getattr(msg, "content", "") or ""
    if isinstance(msg, HumanMessage):
        return msg
    elif isinstance(msg, AIMessage):
        if len(content) > max_chars:
            return AIMessage(content=content[:max_chars] + "...[已截短]")
        return msg
    elif isinstance(msg, ToolMessage):
        return ToolMessage(content="[工具调用结果已省略]", tool_call_id=getattr(msg, "tool_call_id", ""))
    return msg


def assemble_context_messages(
    messages: list[AnyMessage],
    system_prompt: str,
    summary: str | None = None,
    recent_turns: int = 8,
    max_history_tokens: int = 4000,
) -> list[AnyMessage]:
    result: list[AnyMessage] = [SystemMessage(content=system_prompt)]

    if not messages:
        return result

    # Total message count for recent_turns (each turn has ~2 messages: user + assistant)
    tier1_count = recent_turns * 2
    if len(messages) <= tier1_count:
        # All messages fit in Tier 1
        tier1_msgs = messages
        tier2_msgs = []
    else:
        tier2_msgs = messages[:-tier1_count]
        tier1_msgs = messages[-tier1_count:]

    # Truncate Tier 2 middle messages
    truncated_tier2 = [truncate_middle_message(m) for m in tier2_msgs]

    assembled = []
    if summary and summary.strip():
        assembled.append(SystemMessage(content=f"【前序对话背景摘要】：{summary.strip()}"))

    assembled.extend(truncated_tier2)
    assembled.extend(tier1_msgs)

    # Check token budget; if exceeds, drop older tier 2 items
    current_tokens = sum(estimate_tokens(getattr(m, "content", "") or "") for m in assembled)
    while current_tokens > max_history_tokens and truncated_tier2:
        dropped = truncated_tier2.pop(0)
        current_tokens -= estimate_tokens(getattr(dropped, "content", "") or "")

    result.extend(assembled)
    return result


async def generate_summary(
    messages: list[AnyMessage],
    model: Any,
    existing_summary: str | None = None,
) -> str:
    if not messages:
        return existing_summary or ""

    dialog_text = "\n".join(
        f"{m.__class__.__name__}: {getattr(m, 'content', '')}"
        for m in messages
    )
    prompt = [
        SystemMessage(content="你是客服对话摘要助手。请将以下对话关键事实（如提到的订单号、商品、用户诉求、客服结论）提炼为一段简洁的摘要（100字以内），定死不磨掉订单号。"),
        HumanMessage(content=f"已知前情摘要：{existing_summary or '无'}\n\n新增对话：\n{dialog_text}"),
    ]
    try:
        response = await model.ainvoke(prompt)
        return getattr(response, "content", "").strip()
    except Exception:
        return existing_summary or "用户咨询订单及售后事宜"
