import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger("app.core.flywheel")

FLYWHEEL_SYSTEM_PROMPT = """你是一个电商客服知识治理助手。
你的任务是将用户未解决的真实问题进行“标准化归并”，并生成建议的标准答复。
输入：
1. 用户原始问题 (raw_question)
2. 当前待审知识候选列表 (candidates)

输出要求（严格JSON）：
{
  "normalized_question": "标准问句（去掉情绪、订单号、语气词，提炼为通用的标准问题）",
  "matched_candidate_id": 候选ID或null（如果与候选中的某条表达相同含义，则返回该ID，否则null）,
  "ai_suggested_answer": "基于常识和官方规范生成的参考回答"
}
"""


async def process_flywheel_batch(
    flywheel_repository: Any,
    model: Any | None = None,
    batch_size: int = 50,
) -> dict[str, int]:
    unmerged = await flywheel_repository.list_unmerged_questions(limit=batch_size)
    if not unmerged:
        return {"processed": 0, "merged": 0, "new_items": 0}

    # Fetch top 200 candidates to prevent context window explosion
    candidate_items = await flywheel_repository.list_review_queue(limit=200)
    candidates_data = [
        {"id": c.id, "normalized_question": c.normalized_question}
        for c in candidate_items
    ]

    processed = 0
    merged = 0
    new_items = 0

    for q in unmerged:
        raw_text = q.raw_question.strip()
        matched_id = None
        normalized = raw_text
        suggested_answer = "感谢您的反馈，该问题正在整理官方答复中。"

        # 1. Rule-based or fast match first
        for c in candidates_data:
            if c["normalized_question"] == raw_text or raw_text in c["normalized_question"]:
                matched_id = c["id"]
                normalized = c["normalized_question"]
                break

        # 2. If no exact match and model available, invoke LLM
        if matched_id is None and model is not None:
            try:
                prompt = [
                    SystemMessage(content=FLYWHEEL_SYSTEM_PROMPT),
                    HumanMessage(
                        content=f"用户提问：{raw_text}\n现有候选：{json.dumps(candidates_data, ensure_ascii=False)}"
                    ),
                ]
                resp = await model.ainvoke(prompt)
                content = getattr(resp, "content", "").strip()
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    normalized = parsed.get("normalized_question") or raw_text
                    cid = parsed.get("matched_candidate_id")
                    if cid and any(c["id"] == cid for c in candidates_data):
                        matched_id = cid
                    if parsed.get("ai_suggested_answer"):
                        suggested_answer = parsed.get("ai_suggested_answer")
            except Exception as e:
                logger.warning("Flywheel LLM normalization failed for question %d: %s", q.id, e)

        # 3. Save to repository
        if matched_id is not None:
            # Increment occurrence
            item = await flywheel_repository.get_or_create_review_item(normalized)
            await flywheel_repository.mark_question_matched(q.id, matched_id)
            merged += 1
        else:
            # New review item
            item = await flywheel_repository.get_or_create_review_item(
                normalized_question=normalized,
                ai_suggested_answer=suggested_answer,
            )
            candidates_data.append({"id": item.id, "normalized_question": item.normalized_question})
            await flywheel_repository.mark_question_matched(q.id, item.id)
            new_items += 1

        processed += 1

    return {"processed": processed, "merged": merged, "new_items": new_items}
