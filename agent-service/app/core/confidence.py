from typing import Any

W_TOP1 = 0.5
W_VALID = 0.2
W_MARGIN = 0.2
W_KEY = 0.1

DEFAULT_CONFIDENCE_THRESHOLD = 0.26
VALID_SCORE_THRESHOLD = 0.3


def compute_evidence_confidence(
    evidence_chunks: list[dict],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, Any]:
    if not evidence_chunks:
        return {
            "score": 0.0,
            "is_confident": False,
            "top1_score": 0.0,
            "valid_count": 0,
            "margin": 0.0,
            "key_clause_hit": 0.0,
            "threshold": threshold,
        }

    # Sort chunks by score descending
    sorted_chunks = sorted(evidence_chunks, key=lambda c: c.get("score", 0.0), reverse=True)

    top1_score = float(sorted_chunks[0].get("score", 0.0))
    top2_score = float(sorted_chunks[1].get("score", 0.0)) if len(sorted_chunks) > 1 else 0.0

    # 1. Top1 score
    s1 = top1_score

    # 2. Valid count (score >= 0.3, capped at 3)
    valid_count = sum(1 for c in sorted_chunks if c.get("score", 0.0) >= VALID_SCORE_THRESHOLD)
    s2 = min(valid_count, 3) / 3.0

    # 3. Margin between top1 and top2
    margin = max(0.0, top1_score - top2_score)
    s3 = margin

    # 4. Key clause hit in top 3
    key_clause_hit = 1.0 if any(c.get("is_key_clause", False) for c in sorted_chunks[:3]) else 0.0
    s4 = key_clause_hit

    final_score = (
        W_TOP1 * s1
        + W_VALID * s2
        + W_MARGIN * s3
        + W_KEY * s4
    )
    final_score = round(min(1.0, max(0.0, final_score)), 4)
    is_confident = final_score >= threshold

    return {
        "score": final_score,
        "is_confident": is_confident,
        "top1_score": top1_score,
        "valid_count": valid_count,
        "margin": round(margin, 4),
        "key_clause_hit": key_clause_hit,
        "threshold": threshold,
    }
