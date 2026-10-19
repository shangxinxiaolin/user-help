import hashlib
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("app.kb.mining")

MINING_SYSTEM_PROMPT = """你是一个电商客服对话知识提炼专家。
你的任务是从真实客服对话历史中，抽取具有普遍参考价值、可复用的问答对 (QA pairs)。
规则：
1. 过滤掉包含具体私密信息（如特定手机号、收货地址、特定订单号1001）的答复，泛化为通用规则。
2. 过滤掉无意义的寒暄（如“在吗”、“稍等我看下”）。
3. 必须成对抽取通用问句和标准回答。

输出严格JSON格式：
{
  "qa_pairs": [
    {"question": "通用问句", "answer": "通用回答"}
  ]
}
"""


def compute_qa_fingerprint(question: str, answer: str) -> str:
    norm = (question.strip() + "###" + answer.strip()).lower()
    return hashlib.md5(norm.encode("utf-8")).hexdigest()


async def mine_qa_from_messages(
    messages: list[Any],
    model: Any | None = None,
) -> list[dict[str, str]]:
    if not messages or len(messages) < 2:
        return []

    # Format dialogue text
    lines = []
    for m in messages:
        role = getattr(m, "role", None) or m.__class__.__name__
        content = getattr(m, "content", "") or ""
        if content.strip():
            lines.append(f"{role}: {content.strip()}")
    dialogue_text = "\n".join(lines)

    qa_pairs = []
    if model is not None:
        try:
            prompt = [
                SystemMessage(content=MINING_SYSTEM_PROMPT),
                HumanMessage(content=f"对话历史：\n{dialogue_text}"),
            ]
            resp = await model.ainvoke(prompt)
            content = getattr(resp, "content", "").strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                for item in data.get("qa_pairs", []):
                    q = item.get("question", "").strip()
                    a = item.get("answer", "").strip()
                    if q and a:
                        qa_pairs.append({"question": q, "answer": a})
        except Exception as e:
            logger.warning("LLM mining failed: %s", e)

    # Fallback heuristic: simple question/answer pairs from consecutive user/assistant messages
    if not qa_pairs:
        for i in range(len(messages) - 1):
            curr = messages[i]
            nxt = messages[i + 1]
            c_role = getattr(curr, "role", "") or curr.__class__.__name__
            n_role = getattr(nxt, "role", "") or nxt.__class__.__name__
            if ("user" in str(c_role).lower() or "human" in str(c_role).lower()) and \
               ("assistant" in str(n_role).lower() or "ai" in str(n_role).lower()):
                q_text = getattr(curr, "content", "") or ""
                a_text = getattr(nxt, "content", "") or ""
                if len(q_text) >= 4 and len(a_text) >= 10:
                    qa_pairs.append({"question": q_text.strip(), "answer": a_text.strip()})

    return qa_pairs


async def run_mining_pipeline(
    conversation_repository: Any,
    knowledge_repository: Any,
    model: Any | None = None,
    limit_conversations: int = 20,
) -> dict[str, int]:
    extracted_count = 0
    discarded_count = 0

    # Get recent staging fingerprints for deduplication
    existing_staging = await knowledge_repository.list_qa_staging(limit=500)
    seen_fingerprints = {s.fingerprint for s in existing_staging}

    # Fetch conversations
    # For demo/test, list messages from conversation IDs or passed conversations
    # Here we simulate mining across recent conversation records
    return {"extracted": extracted_count, "discarded": discarded_count}
