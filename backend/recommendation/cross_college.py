"""Cross-college comparison: query multiple tenant ChromaDB collections."""
from knowledge_base.retriever import retrieve_candidates


async def cross_college_recommendations(
    profile: dict, tenant_slugs: list[str], top_n: int = 10
) -> list[dict]:
    results = []
    for slug in tenant_slugs:
        try:
            candidates = retrieve_candidates(profile, k=10, tenant_slug=slug)
        except Exception:
            continue
        if not candidates:
            continue
        avg_dist = sum(c.get("distance", 0) for c in candidates) / len(candidates)
        results.append({
            "tenant_slug": slug,
            "majors": [c["metadata"] for c in candidates[:3]],
            "match_score": round(100 - avg_dist * 100, 1),
        })
    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results[:top_n]
