"""Per-tenant ChromaDB indexing utilities."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from knowledge.client import get_chroma_client
from knowledge.index_lock import get_lock, get_progress, set_progress, is_running
from knowledge_base.embeddings import embedding_model
from tenants.models import TenantData

logger = logging.getLogger(__name__)


def _build_document_text(data: TenantData) -> str:
    """Convert a TenantData record to a searchable text blob."""
    parts = [data.title]
    content = data.content or {}

    if data.data_type == "admission_score":
        parts.append(
            f"{content.get('major_name', '')} "
            f"{data.year or ''}年 "
            f"{data.province or ''} "
            f"最低分{content.get('min_score', '')} "
            f"最低位次{content.get('min_rank', '')} "
            f"选科要求{content.get('subject_requirements', '')}"
        )
    elif data.data_type == "curriculum":
        courses = content.get("core_courses", [])
        if isinstance(courses, list):
            parts.append(" ".join(str(c) for c in courses))
        else:
            parts.append(str(courses))
        obj = content.get("objective", "")
        parts.append(obj if isinstance(obj, str) else str(obj))
    elif data.data_type == "employment":
        top_ind = content.get("top_industries", [])
        ind_text = ""
        if isinstance(top_ind, list):
            ind_text = " ".join(
                f"{i.get('industry', '')}({i.get('percentage', 0)*100:.0f}%)"
                for i in top_ind[:5]
            )
        parts.append(
            f"就业率{content.get('employment_rate', '')} "
            f"月薪{content.get('avg_monthly_salary', '')} "
            f"行业: {ind_text}"
        )
    elif data.data_type == "campus_life":
        category = content.get("category", "")
        sub_category = content.get("sub_category", "")
        topic = content.get("topic", "") or sub_category
        summary = content.get("summary", "")
        keywords = content.get("keywords", [])
        qa = content.get("qa", [])
        # 新 RAG 知识库格式字段
        question_patterns = content.get("question_patterns", [])
        answer_content = content.get("answer_content", "")
        chunk_id = content.get("chunk_id", "")
        if isinstance(keywords, list):
            keywords = " ".join(str(k) for k in keywords)
        if isinstance(qa, list):
            qa_text = " ".join(
                f"问:{item.get('question', '')} 答:{item.get('answer', '')}"
                for item in qa
                if isinstance(item, dict)
            )
        else:
            qa_text = str(qa)
        if isinstance(question_patterns, list):
            patterns_text = " ".join(f"问:{q}" for q in question_patterns if q)
        else:
            patterns_text = str(question_patterns)
        parts.append(
            " ".join(
                str(p)
                for p in [
                    chunk_id,
                    category,
                    sub_category,
                    topic,
                    summary,
                    answer_content,
                    patterns_text,
                    content.get("text", ""),
                    qa_text,
                    keywords,
                    content.get("source_title", ""),
                    content.get("source", ""),
                    content.get("source_url", ""),
                ]
                if p
            )
        )

    return " ".join(str(p) for p in parts if p)


def _sanitize_meta_val(v):
    """Replace None with empty string for ChromaDB compatibility."""
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, ensure_ascii=False, default=str)


async def index_tenant_data(tenant_slug: str, data: TenantData) -> None:
    """Index a single TenantData record into the tenant's ChromaDB collection."""
    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"
    collection = client.get_or_create_collection(collection_name)

    doc_text = _build_document_text(data)
    content = data.content or {}
    raw_meta = {
        **data.extra_meta,
        "tenant_slug": tenant_slug,
        "data_type": str(data.data_type) if hasattr(data.data_type, "value") else data.data_type,
        "year": data.year,
        "province": data.province,
        "source_title": content.get("source_title", ""),
        "source_url": content.get("source_url", data.source_url or ""),
    }
    embedding = embedding_model.embed_documents([doc_text])
    clean_meta = {k: _sanitize_meta_val(v) for k, v in raw_meta.items()}
    collection.add(
        ids=[str(data.id)],
        embeddings=embedding,
        documents=[doc_text],
        metadatas=[clean_meta],
    )


async def reindex_tenant(tenant_slug: str, triggered_by: str = "manual") -> bool:
    """Drop and rebuild a tenant's entire ChromaDB collection.

    Call this after bulk-importing TenantData records.

    保障机制：
    1. per-tenant asyncio.Lock 防止并发 reindex（ChromaDB collection 删除/重建会冲突）
    2. 同步阻塞操作（embedding 推理、ChromaDB add）通过 asyncio.to_thread 包装，
       不阻塞 event loop
    3. 实时更新 in-memory 进度状态，供前端可视化

    Args:
        tenant_slug: 租户标识
        triggered_by: 触发来源（manual / startup / raw_edit），仅用于日志和进度展示

    Returns:
        True 表示成功完成；False 表示因锁占用而跳过
    """
    lock = get_lock(tenant_slug)
    if lock.locked():
        logger.warning(
            "reindex_tenant(%s) skipped: another reindex is running (triggered_by=%s)",
            tenant_slug, triggered_by,
        )
        return False

    async with lock:
        set_progress(
            tenant_slug,
            status="running",
            total=0,
            done=0,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            error=None,
            triggered_by=triggered_by,
        )

        try:
            await _reindex_impl(tenant_slug)
            set_progress(
                tenant_slug,
                status="completed",
                finished_at=datetime.now(timezone.utc),
            )
            return True
        except Exception as e:
            logger.exception("reindex_tenant(%s) failed", tenant_slug)
            set_progress(
                tenant_slug,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error=str(e),
            )
            raise


async def _reindex_impl(tenant_slug: str) -> None:
    """实际的 reindex 逻辑 — 全部同步操作通过 to_thread 包装。"""
    from models import async_session
    from sqlalchemy import select

    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"

    # 删除旧 collection（同步，但通常很快）
    def _delete():
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    await asyncio.to_thread(_delete)

    # 拉取所有 TenantData 记录（async I/O，不阻塞）
    async with async_session() as db:
        from tenants.models import Tenant

        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            return
        result = await db.execute(select(TenantData).where(TenantData.tenant_id == tenant.id))
        records = result.scalars().all()

    set_progress(tenant_slug, total=len(records))

    if not records:
        return

    # 同步 CPU/IO 密集操作 → 放到线程池，不阻塞 event loop
    def _build_batch(batch):
        batch_docs = [_build_document_text(r) for r in batch]
        batch_embeddings = embedding_model.embed_documents(batch_docs)
        batch_ids = [str(r.id) for r in batch]
        batch_metas = [
            {
                **{k: _sanitize_meta_val(v) for k, v in r.extra_meta.items()},
                "tenant_slug": tenant_slug,
                "data_type": str(r.data_type) if hasattr(r.data_type, "value") else r.data_type,
                "year": _sanitize_meta_val(r.year),
                "province": _sanitize_meta_val(r.province),
                "source_title": (r.content or {}).get("source_title", ""),
                "source_url": (r.content or {}).get("source_url", r.source_url or ""),
            }
            for r in batch
        ]
        return batch_ids, batch_embeddings, batch_docs, batch_metas

    def _add_batch(collection, batch_ids, batch_embeddings, batch_docs, batch_metas):
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_metas,
        )

    # 在线程池中创建 collection 并分批写入
    def _index_all():
        collection = client.get_or_create_collection(collection_name)
        batch_size = 64  # 较小批次便于实时进度更新
        all_ids = []
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            ids, embs, docs, metas = _build_batch(batch)
            _add_batch(collection, ids, embs, docs, metas)
            all_ids.extend(ids)
            # 更新进度（set_progress 是普通 dict 操作，GIL 保护下线程安全）
            set_progress(tenant_slug, done=min(i + batch_size, len(records)))
        return all_ids

    all_ids = await asyncio.to_thread(_index_all)

    # 确保最终进度准确
    set_progress(tenant_slug, done=len(records))

    # 标记 PostgreSQL 中的 indexed_at（async I/O）
    if all_ids:
        from models import async_session as _as
        from sqlalchemy import text as _text
        async with _as() as _db:
            await _db.execute(
                _text("UPDATE tenant_data SET indexed_at = :now WHERE id = ANY(:ids)"),
                {"now": datetime.now(timezone.utc), "ids": all_ids},
            )
            await _db.commit()
