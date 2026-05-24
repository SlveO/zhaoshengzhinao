"""Per-tenant ChromaDB indexing utilities."""
from __future__ import annotations

import json

from knowledge.client import get_chroma_client
from knowledge_base.embeddings import embedding_model
from tenants.models import TenantData


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
        topic = content.get("topic", "")
        category = content.get("category", "")
        summary = content.get("summary", "")
        keywords = content.get("keywords", [])
        qa = content.get("qa", [])
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
        parts.append(
            " ".join(
                str(p)
                for p in [
                    category,
                    topic,
                    summary,
                    content.get("text", ""),
                    qa_text,
                    keywords,
                    content.get("source_title", ""),
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


async def reindex_tenant(tenant_slug: str) -> None:
    """Drop and rebuild a tenant's entire ChromaDB collection.

    Call this after bulk-importing TenantData records.
    """
    from models import async_session
    from sqlalchemy import select

    client = get_chroma_client()
    collection_name = f"{tenant_slug}_colleges"

    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    async with async_session() as db:
        from tenants.models import Tenant

        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            return
        result = await db.execute(select(TenantData).where(TenantData.tenant_id == tenant.id))
        records = result.scalars().all()

    if not records:
        return

    collection = client.get_or_create_collection(collection_name)
    batch_size = 2000
    all_ids = []
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        batch_docs = [_build_document_text(r) for r in batch]
        batch_embeddings = embedding_model.embed_documents(batch_docs)
        batch_ids = [str(r.id) for r in batch]
        all_ids.extend(batch_ids)
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=[
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
            ],
        )

    # Mark all records as indexed in PostgreSQL
    if all_ids:
        from datetime import datetime, timezone
        from models import async_session as _as
        from sqlalchemy import text as _text
        async with _as() as _db:
            await _db.execute(
                _text("UPDATE tenant_data SET indexed_at = :now WHERE id = ANY(:ids)"),
                {"now": datetime.now(timezone.utc), "ids": all_ids},
            )
            await _db.commit()
