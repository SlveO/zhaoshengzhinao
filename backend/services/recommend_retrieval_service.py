"""推荐模块 RAG 检索服务。

为推荐聊天 WebSocket 和报考建议列表提供 ChromaDB 向量检索。
与 consult 模块的检索分离，保持模块独立性。

两个检索函数：
- retrieve_for_chat: 轻量检索，top_k=3，跳过意图抽取，目标延迟 <300ms
- retrieve_for_recommendations: 增强检索，top_k=5，用于丰富推荐理由
"""
import logging
from knowledge_base.chroma_client import search_similar

_logger = logging.getLogger(__name__)


def format_rag_context(sources: list[dict], max_chars: int = 800) -> str:
    """格式化检索结果为 prompt 注入文本。

    输出格式：
        1. {source_title}
        {text}

        2. {source_title}
        {text}

    Args:
        sources: search_similar 返回的列表项
        max_chars: 总字符上限，超出截断

    Returns:
        格式化后的字符串；无检索结果返回"暂无相关官方信息参考"
    """
    if not sources:
        return "暂无相关官方信息参考"

    lines = []
    total = 0
    for i, src in enumerate(sources, start=1):
        text = (src.get("document") or "").strip()
        if not text:
            continue
        meta = src.get("metadata") or {}
        title = meta.get("source_title") or meta.get("title") or "学校官方资料"
        block = f"{i}. {title}\n{text}"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > 50:
                block = block[:remaining] + "…"
            else:
                break
        lines.append(block)
        total += len(block) + 2  # +2 for newline
        if total >= max_chars:
            break

    return "\n\n".join(lines) if lines else "暂无相关官方信息参考"


async def retrieve_for_chat(
    user_content: str,
    tenant_slug: str,
    user_slots: dict,
    top_k: int = 3,
) -> list[dict]:
    """推荐聊天用 — 轻量检索。

    直接用 user_content + slots 上下文做向量检索，
    返回 top_k 相关片段（学校介绍/专业/政策）。
    不走意图抽取，保持低延迟（<300ms）。

    Args:
        user_content: 用户当前消息文本
        tenant_slug: 租户 slug（必填，用于租户隔离的 ChromaDB collection）
        user_slots: 用户画像快照（含 riasec / values / region 等），用于增强查询
        top_k: 返回条数，默认 3

    Returns:
        search_similar 格式的列表项 [{document, metadata, distance}, ...]
        失败返回空列表（chat 路由会优雅降级为空 knowledge_context）
    """
    if not user_content.strip():
        return []

    query_parts = [user_content]
    riasec = user_slots.get("riasec", {})
    if riasec:
        top_dims = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        dim_keywords = {
            "R": "动手操作 工程 技术",
            "I": "研究 科学 分析",
            "A": "设计 创意 艺术",
            "S": "教育 服务 社会",
            "E": "管理 商业 金融",
            "C": "数据 规范 行政",
        }
        kw = " ".join(dim_keywords.get(d, "") for d, _ in top_dims)
        if kw:
            query_parts.append(kw)

    if user_slots.get("region_pref"):
        regions = user_slots["region_pref"].get("regions", [])
        if regions:
            query_parts.append(" ".join(regions[:2]))

    query = " ".join(query_parts)

    try:
        results = search_similar(query, k=top_k, tenant_slug=tenant_slug)
        _logger.debug(
            "retrieve_for_chat: query=%r tenant=%s returned %d results",
            query[:80], tenant_slug, len(results),
        )
        return results
    except Exception as e:
        _logger.warning("retrieve_for_chat failed: %s", e)
        return []


async def retrieve_for_recommendations(
    profile: dict,
    tenant_slug: str,
    existing_candidates: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """报考建议列表用 — 增强文本型检索。

    在现有 retrieve_candidates（院校专业 metadata）基础上，
    追加文本型 RAG（学校介绍/招生政策），用于丰富推荐理由。

    Args:
        profile: 学生画像快照
        tenant_slug: 租户 slug
        existing_candidates: retrieve_candidates 已返回的候选列表（用于聚焦查询）
        top_k: 返回条数，默认 5

    Returns:
        search_similar 格式的列表项
    """
    query_parts = []

    college_names = set()
    major_names = set()
    for c in existing_candidates[:5]:
        meta = c.get("metadata", {})
        if meta.get("college_name"):
            college_names.add(meta["college_name"])
        if meta.get("major_name"):
            major_names.add(meta["major_name"])

    if college_names:
        query_parts.append(" ".join(list(college_names)[:3]))
    if major_names:
        query_parts.append(" ".join(list(major_names)[:3]))

    riasec = profile.get("riasec", {})
    if riasec:
        top_dims = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        dim_keywords = {
            "R": "动手操作 工程 技术",
            "I": "研究 科学 分析",
            "A": "设计 创意 艺术",
            "S": "教育 服务 社会",
            "E": "管理 商业 金融",
            "C": "数据 规范 行政",
        }
        kw = " ".join(dim_keywords.get(d, "") for d, _ in top_dims)
        if kw:
            query_parts.append(kw)

    if not query_parts:
        return []

    query = " ".join(query_parts)

    try:
        results = search_similar(query, k=top_k, tenant_slug=tenant_slug)
        _logger.debug(
            "retrieve_for_recommendations: query=%r tenant=%s returned %d results",
            query[:80], tenant_slug, len(results),
        )
        return results
    except Exception as e:
        _logger.warning("retrieve_for_recommendations failed: %s", e)
        return []
