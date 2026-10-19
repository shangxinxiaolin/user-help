import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

TAXONOMY_CATEGORIES = [
    "退换货",
    "物流时效",
    "运费与包邮",
    "发票开具",
    "保修售后",
    "商品参数",
    "其他",
]

TAXONOMY_PROMPT = """你是一个电商客服问题多标签主题归类助手。
请根据用户问题，判断其包含哪些主题（提到几个标几个，多标签）。
可选标签：
- 退换货：退款、退货、换货、上门取件
- 物流时效：发货时间、快递慢、催单、派送
- 运费与包邮：满减包邮、偏远地区邮费、退货运费险
- 发票开具：电子发票、专票、开票时间
- 保修售后：在保状态、维修、质保期、三包
- 商品参数：尺寸、颜色、功能、用法、续航
- 其他：无法归入上述标签的内容

返回严格JSON：
{"topics": ["退换货"], "confidence": 0.95}
"""


def rule_based_taxonomy(question: str) -> list[str]:
    q = question.strip()
    topics = []
    if any(k in q for k in ["退货", "退款", "退钱", "换货"]):
        topics.append("退换货")
    if any(k in q for k in ["发货", "快递", "物流", "慢", "几天到"]):
        topics.append("物流时效")
    if any(k in q for k in ["运费", "包邮", "邮费"]):
        topics.append("运费与包邮")
    if any(k in q for k in ["发票", "开票", "专票", "普票"]):
        topics.append("发票开具")
    if any(k in q for k in ["保修", "质保", "维修", "坏了"]):
        topics.append("保修售后")
    if any(k in q for k in ["参数", "电池", "颜色", "功能", "规格"]):
        topics.append("商品参数")

    return topics if topics else ["其他"]


async def classify_topics(
    question: str,
    model: Any | None = None,
) -> tuple[list[str], float]:
    if not question or not question.strip():
        return ["其他"], 1.0

    if model is not None:
        try:
            prompt = [
                SystemMessage(content=TAXONOMY_PROMPT),
                HumanMessage(content=f"用户提问：{question}"),
            ]
            resp = await model.ainvoke(prompt)
            content = getattr(resp, "content", "").strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                topics = [t for t in data.get("topics", []) if t in TAXONOMY_CATEGORIES]
                confidence = float(data.get("confidence", 0.9))
                if topics:
                    return topics, confidence
        except Exception:
            pass

    return rule_based_taxonomy(question), 0.85
