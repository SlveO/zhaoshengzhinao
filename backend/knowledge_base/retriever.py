"""Hybrid retrieval: semantic (Chroma) + rule-based filtering."""
from knowledge_base.chroma_client import search_similar


def build_query_text(profile: dict) -> str:
    parts = []
    riasec = profile.get("riasec", {})
    if riasec:
        top_dims = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:3]
        dim_keywords = {
            "R": "动手操作 工程 技术 实验",
            "I": "研究 科学 分析 探索",
            "A": "设计 创意 艺术 表达",
            "S": "帮助 教育 医疗 服务 社会",
            "E": "管理 领导 商业 金融",
            "C": "规范 数据 会计 行政 组织",
        }
        kw = " ".join(dim_keywords.get(d, "") for d, _ in top_dims)
        parts.append(kw)
    if profile.get("career_vision"):
        parts.append(profile["career_vision"])
    if profile.get("values"):
        parts.append(" ".join(profile["values"]))
    return " ".join(parts) if parts else "综合 大学 本科"


def retrieve_candidates(profile: dict, k: int = 30) -> list[dict]:
    query = build_query_text(profile)
    candidates = search_similar(query, k=max(k * 3, 100))
    raw = (profile.get("subjects", "") or "").replace("+", " ").split()
    user_subjects = {s for s in raw if s}
    filtered = []
    for item in candidates:
        meta = item["metadata"]
        raw_req = (meta.get("subjects", "") or "").replace("+", " ").split()
        req = {s for s in raw_req if s}
        if not user_subjects or not req or req == {"不限"} or user_subjects & req:
            filtered.append(item)
    # Diversity: keep at most 3 results per college
    seen = {}
    diverse = []
    for item in filtered:
        cid = item["metadata"].get("college_id", "unknown")
        if seen.get(cid, 0) < 3:
            seen[cid] = seen.get(cid, 0) + 1
            diverse.append(item)
    return diverse[:k]
