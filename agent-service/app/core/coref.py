import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

COREF_SYSTEM_PROMPT = """你是一个电商客服指代消解助手。
根据最近的对话历史，把用户最新一句话中的代词（如“这个”、“那个”、“它”、“那个订单”）替换为具体指代的对象（如具体订单号、商品名称）。
规则：
1. 如果用户的问题已经很明确完整，无需改写，原样返回。
2. 只能使用历史对话中明确出现过的信息，绝不能无中生有。
3. 直接返回消解后的完整问题，不要加多余的解释。
"""


def rule_based_coref(query: str, history: list[Any]) -> str:
    cleaned = query.strip()
    pronouns = ["这个", "那个", "它", "那个订单", "这单", "那单"]
    has_pronoun = any(p in cleaned for p in pronouns)
    if not has_pronoun:
        return cleaned

    # Search backwards for order ID pattern in history
    order_id = None
    product_name = None
    for msg in reversed(history):
        content = getattr(msg, "content", "")
        if not content:
            continue
        order_match = re.search(r"(\b\d{4,10}\b)", content)
        if order_match and not order_id:
            order_id = order_match.group(1)
        if "耳机" in content:
            product_name = "耳机"
        elif "手机" in content:
            product_name = "手机"

    if order_id:
        for p in ["那个订单", "这单", "那单", "这个订单"]:
            if p in cleaned:
                return cleaned.replace(p, f"订单 {order_id}")
        if "这个" in cleaned:
            return cleaned.replace("这个", f"订单 {order_id}")
    if product_name and "这个" in cleaned:
        return cleaned.replace("这个", product_name)

    return cleaned


async def resolve_reference(
    query: str,
    history: list[Any],
    model: Any | None = None,
) -> str:
    if not query or not query.strip():
        return ""

    if not history:
        return query.strip()

    # Try LLM if available and contains pronouns
    pronouns = ["这个", "那个", "它", "那个订单", "这单", "那单"]
    if model is not None and any(p in query for p in pronouns):
        try:
            history_text = "\n".join(
                f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {getattr(m, 'content', '')}"
                for m in history[-6:]
            )
            prompt = [
                SystemMessage(content=COREF_SYSTEM_PROMPT),
                HumanMessage(content=f"历史对话：\n{history_text}\n\n用户当前问题：{query}"),
            ]
            response = await model.ainvoke(prompt)
            result = getattr(response, "content", "").strip()
            if result:
                return result
        except Exception:
            pass

    return rule_based_coref(query, history)
