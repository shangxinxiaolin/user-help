import math
import re
from typing import Any


def _tokenize(text: str) -> list[str]:
    # Character and word-level tokenization for Chinese & English
    tokens = re.findall(r"[\u4e00-\u9fa5]|[a-zA-Z0-9]+", text.lower())
    return tokens


def compute_bm25_scores(
    query_tokens: list[str],
    documents: list[dict],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    n_docs = len(documents)
    if n_docs == 0:
        return []

    doc_tokens_list = [_tokenize(doc.get("content", "") + " " + doc.get("title", "")) for doc in documents]
    doc_lens = [len(dt) for dt in doc_tokens_list]
    avg_len = sum(doc_lens) / n_docs if n_docs > 0 else 1.0

    # DF
    df = {}
    for token in set(query_tokens):
        df[token] = sum(1 for dt in doc_tokens_list if token in dt)

    scores = []
    for dt, dlen in zip(doc_tokens_list, doc_lens):
        score = 0.0
        for token in query_tokens:
            if token not in df or df[token] == 0:
                continue
            tf = dt.count(token)
            idf = math.log((n_docs - df[token] + 0.5) / (df[token] + 0.5) + 1.0)
            numerator = tf * (k1 + 1.0)
            denominator = tf + k1 * (1.0 - b + b * (dlen / avg_len if avg_len > 0 else 1.0))
            score += idf * (numerator / denominator if denominator > 0 else 0.0)
        scores.append(score)

    # Normalize to [0, 1]
    max_s = max(scores) if scores and max(scores) > 0 else 1.0
    return [s / max_s for s in scores]


def compute_dense_sim_scores(query: str, documents: list[dict]) -> list[float]:
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return [0.0] * len(documents)

    scores = []
    for doc in documents:
        d_tokens = set(_tokenize(doc.get("content", "") + " " + doc.get("title", "")))
        if not d_tokens:
            scores.append(0.0)
            continue
        intersection = len(q_tokens.intersection(d_tokens))
        union = len(q_tokens.union(d_tokens))
        jaccard = intersection / union if union > 0 else 0.0
        scores.append(jaccard)

    max_s = max(scores) if scores and max(scores) > 0 else 1.0
    return [s / max_s for s in scores]


def rrf_fusion(
    bm25_ranks: list[int],
    dense_ranks: list[int],
    k: int = 60,
) -> list[float]:
    # RRF = 1/(k + rank1) + 1/(k + rank2)
    scores = []
    for r_b, r_d in zip(bm25_ranks, dense_ranks):
        score = (1.0 / (k + r_b)) + (1.0 / (k + r_d))
        scores.append(score)
    return scores


def hybrid_search(
    query: str,
    documents: list[dict],
    top_k: int = 5,
    use_rerank: bool = True,
) -> list[dict]:
    if not documents or not query.strip():
        return []

    q_tokens = _tokenize(query)
    bm25_scores = compute_bm25_scores(q_tokens, documents)
    dense_scores = compute_dense_sim_scores(query, documents)

    # Get ranks (1-indexed, lower is better)
    bm25_sorted_indices = sorted(range(len(documents)), key=lambda i: bm25_scores[i], reverse=True)
    bm25_ranks = [0] * len(documents)
    for rank, idx in enumerate(bm25_sorted_indices, 1):
        bm25_ranks[idx] = rank

    dense_sorted_indices = sorted(range(len(documents)), key=lambda i: dense_scores[i], reverse=True)
    dense_ranks = [0] * len(documents)
    for rank, idx in enumerate(dense_sorted_indices, 1):
        dense_ranks[idx] = rank

    rrf_scores = rrf_fusion(bm25_ranks, dense_ranks, k=60)

    # Re-ranking adjustments
    ranked_docs = []
    for idx, doc in enumerate(documents):
        base_score = rrf_scores[idx] * 50.0  # scale up for readable score [0, 1]
        raw_score = 0.5 * bm25_scores[idx] + 0.5 * dense_scores[idx]
        final_score = raw_score
        if use_rerank:
            if doc.get("is_key_clause", False):
                final_score += 0.15
            if doc.get("title", "") in query or query in doc.get("title", ""):
                final_score += 0.2

        final_score = min(1.0, max(0.0, final_score))
        doc_copy = dict(doc)
        doc_copy["score"] = round(final_score, 4)
        doc_copy["bm25_score"] = round(bm25_scores[idx], 4)
        doc_copy["dense_score"] = round(dense_scores[idx], 4)
        ranked_docs.append(doc_copy)

    ranked_docs.sort(key=lambda d: d["score"], reverse=True)
    return ranked_docs[:top_k]
