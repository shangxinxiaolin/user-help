import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

INTENT_CLASSES = [
    "订单",
    "物流",
    "退款退货",
    "售后",
    "商品咨询",
    "投诉",
    "闲聊",
    "人工",
    "其他",
]

INTENT_SYSTEM_PROMPT = """你是一个电商客服意图识别专家。根据用户的提问，判断用户的核心意图。
只能从以下9个意图中选择一个：
- 订单：查询订单详情、买过的东西、金额、修改订单等
- 物流：查询快递在哪、派件、物流单号、时效、什么时候到
- 退款退货：退货、退款、退钱、取消订单退款
- 售后：保修期查询、维修、换货、退货进度
- 商品咨询：商品规格、功能、运费规则、优惠券、发票等常见政策咨询
- 投诉：态度恶劣、产品严重问题、要求赔偿、打消费者热线
- 闲聊：打招呼、问好、讲笑话、无关聊天
- 人工：要求转人工客服、找真人、人工服务
- 其他：无法分类的内容

输出必须为严格的 JSON 格式：
{"intent": "意图名称", "confidence": 0.95, "reason": "简要理由"}
"""


def rule_based_classify(query: str) -> tuple[str, float, str]:
    q = query.strip()
    if any(k in q for k in ["人工", "真人", "转人工"]):
        return "人工", 0.98, "包含人工关键词"
    if any(k in q for k in ["投诉", "315", "消协", "差评", "太差了", "骗子", "赔偿"]):
        return "投诉", 0.95, "包含投诉关键词"
    if any(k in q for k in ["退款", "退货", "退钱", "想退了", "不要了退"]):
        return "退款退货", 0.95, "包含退款关键词"
    if any(k in q for k in ["物流", "快递", "到哪了", "发货", "单号", "派送"]):
        return "物流", 0.95, "包含物流关键词"
    if any(k in q for k in ["保修", "质保", "坏了", "维修", "换货", "退货进度"]):
        return "售后", 0.90, "包含售后关键词"
    if any(k in q for k in ["订单", "买的", "买了什么", "查单"]):
        return "订单", 0.90, "包含订单关键词"
    if any(k in q for k in ["运费", "发票", "规格", "多少钱", "怎么用", "包邮", "正品"]):
        return "商品咨询", 0.90, "包含商品或政策咨询关键词"
    if any(k in q for k in ["你好", "在吗", "早上好", "哈喽", "hi", "hello", "谢谢"]):
        return "闲聊", 0.95, "包含问候闲聊词"

    return "其他", 0.60, "无明确关键词匹配"


async def classify_intent(
    query: str,
    model: Any | None = None,
) -> tuple[str, float, str]:
    if not query or not query.strip():
        return "其他", 1.0, "空问题"

    if model is not None:
        try:
            prompt = [
                SystemMessage(content=INTENT_SYSTEM_PROMPT),
                HumanMessage(content=f"用户提问：{query}"),
            ]
            response = await model.ainvoke(prompt)
            content = getattr(response, "content", "").strip()
            # Parse json
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                intent = data.get("intent", "其他")
                confidence = float(data.get("confidence", 0.85))
                reason = data.get("reason", "")
                if intent in INTENT_CLASSES:
                    return intent, confidence, reason
        except Exception:
            pass

    return rule_based_classify(query)
