"""M6 — this-or-that feedback + query vector updates."""
import numpy as np

from .config import REL_FEEDBACK


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-12:
        return v
    return v / n


def pick_pair(scored, q_vec, emb, top_n=12):
    """Two images from the top 12 with the lowest mutual cosine similarity,
    both with score above the median of the top 12."""
    top = scored.head(top_n).reset_index(drop=True)
    if len(top) < 2:
        return None
    med = top["score"].median()
    ids = top["img_id"].tolist()
    idx = list(range(len(top)))
    above = [i for i in idx if top.loc[i, "score"] > med]
    if len(above) < 2:
        above = idx
    e = np.asarray(emb, dtype="float32")
    id_to_row = None
    # map img_id -> row in emb (caller must pass emb aligned with meta)
    best = None
    for i in range(len(above)):
        for j in range(i + 1, len(above)):
            a, b = above[i], above[j]
            sim = float(e[a] @ e[b])
            if best is None or sim < best["sim"]:
                best = {"left": ids[a], "right": ids[b], "sim": sim}
    return best


def update_query_vec(q_vec: np.ndarray, pos_ids, neg_ids, emb, img_index: dict):
    """q' = normalize(alpha*q + beta*mean(emb[pos]) - gamma*mean(emb[neg]))"""
    alpha, beta, gamma = REL_FEEDBACK["alpha"], REL_FEEDBACK["beta"], REL_FEEDBACK["gamma"]
    e = np.asarray(emb, dtype="float32")
    q = np.asarray(q_vec, dtype="float32")
    pos = [img_index[i] for i in pos_ids if i in img_index]
    neg = [img_index[i] for i in neg_ids if i in img_index]
    v = alpha * q
    if pos:
        v = v + beta * e[pos].mean(axis=0)
    if neg:
        v = v - gamma * e[neg].mean(axis=0)
    return _unit(v)
